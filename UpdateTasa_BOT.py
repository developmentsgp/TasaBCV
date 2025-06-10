# -*- coding: UTF-8 -*-
###################################################################
# Programa para actualizar la tasa del BCV en SAP
# Adaptado para funcionar como servicio web en Render
# Autor: Marlos E. Gomez
# Creado el: 24/02/2025 03:32 pm
###################################################################

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
import telebot
import schedule
import ssl
import requests
import urllib.request
from bs4 import BeautifulSoup
import locale
from datetime import datetime
import urllib3

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Obtener variables de entorno
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '6313252063:AAHJblx8ncxWqJKoQmaTzPRcqIvaYy6ph3U')
SAP_USER = os.environ.get('SAP_USER', 'WSAPIREST')
SAP_PASSWORD = os.environ.get('SAP_PASSWORD', 'APIR3st@123')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', None)  # Para actualizaciones automáticas

urlBCV = 'https://www.bcv.org.ve/'
idDolar = "dolar"
idEuro = "euro"

urlApiSAP = "https://enlaces.fortiddns.com:44301/sap/bc/zapi_regrate?sap-client=400"
bot = telebot.TeleBot(TELEGRAM_TOKEN)
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

#-- Servidor web para Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Bot BCV-SAP esta activo</h1><p>Servicio ejecutandose correctamente</p>')

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Servidor web iniciado en el puerto {port}")
    httpd.serve_forever()

##########################
### Tareas automaticas ###
##########################
#-- Iniciar tareas
def Start_Task(call):
    global scheduleTaks
    scheduleTaks = True
    mensaje = '<b>Resultados de las Tareas programadas</b>\n\n⏲️ Tareas iniciadas'
    bot.send_message(call.message.chat.id, mensaje, parse_mode="HTML")

#-- Detener tareas
def Stop_Task(call):
    global scheduleTaks
    scheduleTaks = False
    mensaje = '<b>Resultados de las Tareas programadas</b>\n\n🛑 Tareas detenidas'
    bot.send_message(call.message.chat.id, mensaje, parse_mode="HTML")

#-- Ejecutar tareas
def loop_schedule():
    while True:
        if scheduleTaks:
            schedule.run_pending()
        time.sleep(1)

#-- Actualizar tasa
def Update_Tasa(call=None):
    ssl._create_default_https_context = ssl._create_unverified_context

    try:
        page = urllib.request.urlopen(urlBCV)
    except Exception as e:
        error_msg = f'🛑 Error al acceder a BCV: {str(e)}'
        if call:
            bot.send_message(call.message.chat.id, error_msg)
        elif ADMIN_CHAT_ID:
            bot.send_message(ADMIN_CHAT_ID, error_msg)
        return

    soup = BeautifulSoup(page, 'html.parser')

    try:
        dolarSoup = soup.find('div', id=idDolar)
        dolar = dolarSoup.div.strong.text.strip()

        euroSoup = soup.find('div', id=idEuro)
        euro = euroSoup.div.strong.text.strip()

        dateSoup = soup.find('div', class_="dinpro")
        date_str = dateSoup.span.get_text()

        locale.setlocale(locale.LC_TIME, "Spanish_Spain.1252")
        date = datetime.strptime(date_str, "%A, %d %B %Y").strftime("%d/%m/%Y")
    except Exception as e:
        error_msg = f'🛑 Error procesando datos BCV: {str(e)}'
        if call:
            bot.send_message(call.message.chat.id, error_msg)
        elif ADMIN_CHAT_ID:
            bot.send_message(ADMIN_CHAT_ID, error_msg)
        return

    APIurlTasa = f'{urlApiSAP}&FECHA={date}&TASAUSD={dolar}&TASAEUR={euro}'

    try:
        urllib3.disable_warnings()
        petition = requests.get(APIurlTasa, auth=(SAP_USER, SAP_PASSWORD), verify=False, timeout=10)
        
        if petition.status_code == 200:
            result = petition.json()[16]

            if os.environ.get("RENDER"):
                environ = f"Render: {os.environ.get('RENDER_SERVICE_ID', 'ID desconocido')}"
            else:
                environ = f"Local: {os.uname().nodename if hasattr(os, 'uname') else os.getenv('COMPUTERNAME', 'Desconocido')}"

            message = (f'<b>Resultados de Consulta al BCV</b>\n\n'
                    f'📆 Fecha valor: {date}\n\n'
                    f'Tipos de cambio:\n'
                    f'Dólar = {dolar}\n'
                    f'Euro = {euro}\n\n'
                    f'Resultados actualización en SAP:\n'
                    f'{result["MESSAGE"]}\n'
                    f'{result["MESSAGE_V2"]}\n'
                    f'{result["MESSAGE_V4"]}\n'
                    f'{environ}')


                    #f'Render ({os.environ.get('RENDER_SERVICE_ID', 'ID desconocido')})" if os.environ.get("RENDER") else f"Local ({os.uname().nodename if hasattr(os, 'uname') else os.getenv('COMPUTERNAME', 'Desconocido')})')
        else:
            message = f'🛑 Error en SAP: Código {petition.status_code}\n{petition.text}'
        
        if call:
            bot.send_message(call.message.chat.id, message, parse_mode="HTML")
        elif ADMIN_CHAT_ID:
            bot.send_message(ADMIN_CHAT_ID, message, parse_mode="HTML")
            
    except Exception as e:
        error_msg = f'🛑 Error en conexión SAP: {str(e)}'
        if call:
            bot.send_message(call.message.chat.id, error_msg)
        elif ADMIN_CHAT_ID:
            bot.send_message(ADMIN_CHAT_ID, error_msg)

#--------------------------------
#-- Opciones de actualización ---
#--------------------------------
@bot.message_handler(commands=['start'])
def inicio(mensaje):
    MarkupButtons = MakeMainMarkupButtons()
    bot.send_message(mensaje.chat.id, 'Selecciona una opción', reply_markup=MarkupButtons)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'task_start':
        Start_Task(call)
    elif call.data == 'task_stop':
        Stop_Task(call)
    elif call.data == 'tasa':
        Update_Tasa(call)

def InitBot():
    bot.infinity_polling()

if __name__ == '__main__':
    print('Iniciando aplicación...')
    
    # Configurar tareas programadas
    schedule.every().day.at("06:00").do(Update_Tasa)
    schedule.every().day.at("18:00").do(Update_Tasa)
    
    # Iniciar hilo para tareas programadas
    scheduler_thread = threading.Thread(target=loop_schedule, daemon=True)
    scheduler_thread.start()
    
    # Iniciar bot de Telegram en segundo plano
    bot_thread = threading.Thread(target=InitBot, daemon=True)
    bot_thread.start()
    
    # Iniciar servidor web principal
    run_web_server()
