# -*- coding: UTF-8 -*-
###################################################################
# Programa para actualizar la tasa del BCV en SAP
# Autor: Marlos E. Gomez
# Creado el: 24/02/2025 03:32 pm
###################################################################

#from config import *

import telebot
import threading
import schedule
import time
import ssl
import requests
import urllib.request
from bs4 import BeautifulSoup
import locale
from datetime import datetime
import urllib3

from telebot.types import InlineKeyboardMarkup   # botones
from telebot.types import ReplyKeyboardMarkup   #botones replicar
from telebot.types import InlineKeyboardButton   #botones en linea, debajo


urlBCV = 'https://www.bcv.org.ve/'
idDolar = "dolar"
idEuro = "euro"

urlApiSAP = "https://enlaces.fortiddns.com:44301/sap/bc/zapi_regrate?sap-client=400"
SAPUser = "WSAPIREST"
SAPPassword = "APIR3st@123"


#bot = telebot.TeleBot(TELEGRAM_TOKEN)
bot = telebot.TeleBot("6313252063:AAHJblx8ncxWqJKoQmaTzPRcqIvaYy6ph3U")
scheduleTaks = False

###################################################
#-- Funciones
###################################################

#-- Definicion de botones principales
def MakeMainMarkupButtons():
    markup = InlineKeyboardMarkup(row_width=4)

    btnTaskIni = InlineKeyboardButton('🟢 Iniciar tarea', callback_data='task_start')
    btnTaskStop = InlineKeyboardButton('🔴 Detener tarea', callback_data='task_stop')

    btnUpdTasa = InlineKeyboardButton('⚙️ Actualizar Tasa', callback_data='tasa')

    markup.add(btnTaskIni, btnTaskStop)
    markup.add(btnUpdTasa)

    return markup


##########################
### Tareas automaticas ###
##########################
#-- Iniciar tareas
def Start_Task(call):
    global scheduleTaks
    scheduleTaks = True

    mensaje = ('<b>Resultados de las Tareas programadas</b>' + 
        '\n \n' +
        f'⏲️ Tareas iniciadas')

    bot.send_message(call.message.chat.id, mensaje, parse_mode="HTML")


#-- Detener tareas
def Stop_Task(call):
    global scheduleTaks
    scheduleTaks = False

    mensaje = ('<b>Resultados de las Tareas programadas</b>' + 
        '\n \n' +
        f'🛑 Tareas detenidas')

    bot.send_message(call.message.chat.id, mensaje, parse_mode="HTML")


#-- Ejecutar tareas
def loop_schedule():
    while scheduleTaks:
        schedule.run_pending()
        time.sleep(1)

#-- Actualizar tasa
def Update_Tasa(call):
    ssl._create_default_https_context = ssl._create_unverified_context

    try:
        page = urllib.request.urlopen(urlBCV)
    except requests.exceptions.HTTPError as errH: 
        print(f'Error de HTTP: {page.status_code} | {errH}'.json())
    except requests.exceptions.RequestException as errX:
        print(f'Error: {page.status_code} | {errX}'.json())

    soup = BeautifulSoup(page, 'html.parser')

    dolarSoup = soup.find('div', id = idDolar)
    dolar = dolarSoup.div.strong.text.strip()

    euroSoup = soup.find('div', id = idEuro)
    euro = euroSoup.div.strong.text.strip()

    dateSoup = soup.find('div', class_="dinpro")
    date_str = dateSoup.span.get_text()

    locale.setlocale(locale.LC_TIME, "Spanish_Spain.1252")
    date = datetime.strptime(date_str, "%A, %d %B %Y").strftime("%d/%m/%Y")

    APIurlTasa = f'{urlApiSAP}&FECHA={date}&TASAUSD={dolar}&TASAEUR={euro}'     
    
    try:
        urllib3.disable_warnings() # disable ssl verification
        petition = requests.get(APIurlTasa, auth=(SAPUser, SAPPassword), verify=False)
        result = (petition.json()[16])

        if petition.status_code == 200:
            message = ('<b>Resultados de Consulta al BCV</b>' + '\n \n' +
                f'📆Fecha valor: {date}' + '\n \n' +
                'Tipos de cambio:' + '\n' +
                f'Dólar = {dolar}' + '\n' +
                f'Euro = {euro}'+ '\n \n' +
            
            'Resultados actualización en SAP:' + '\n' +
            f'{result["MESSAGE"]}' + '\n' +
            f'{result["MESSAGE_V2"]}' + '\n' +
            f'{result["MESSAGE_V4"]}')

            bot.send_message(call.message.chat.id, message, parse_mode="HTML")
        else:
            bot.send_message(call.message.chat.id, f'🛑 Error: {petition.text}') 
        
    except requests.exceptions.Timeout as errT:
        bot.send_message(call.message.chat.id, f'🛑 Error de tiempo: {petition.status_code} | {errT}'.json())
    except requests.exceptions.HTTPError as errH: 
        bot.send_message(call.message.chat.id, f'🛑 Error de HTTP: {petition.status_code} | {errH}'.json())
    except requests.exceptions.RequestException as errX:
        bot.send_message(call.message.chat.id, f'🛑 Error: {petition.status_code} | {errX}'.json())



#--------------------------------
#-- Opciones de actualización ---
#--------------------------------
#-- Funcion de respuesta del comando start
@bot.message_handler(commands=['start'])
def inicio(mensaje):
    MarkupButtons = MakeMainMarkupButtons()
    bot.send_message(mensaje.chat.id, 'Selecciona una opción', reply_markup=MarkupButtons)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Si se presiona el boton anterior ⬅️

    if call.data.startswith('task_start'):
        #-- Se activan las tareas automaticas
        Start_Task(call)
    
    elif call.data.startswith('task_stop'):
        Stop_Task(call)

    elif call.data.startswith('tasa'):
        #-- Actualizar tasa
        Update_Tasa(call)



def InitBot():
    bot.infinity_polling()


if __name__ == '__main__':
    print('Iniciando bot')

    # Creación del booleano que indica si el hilo secundario debe correr o no
    timer_runs = threading.Event()

    #-- Tareas programadas
    schedule.every().day.at("06:00").do(Update_Tasa)
    schedule.every().day.at("18:00").do(Update_Tasa)

    hilo_inicio = threading.Thread(name='bot', target=InitBot)
    hilo_inicio.start()

