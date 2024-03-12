import os
import sys
import pandas as pd
import numpy as np 
import requests
from io import BytesIO
from glob import glob
from PIL import Image, ImageEnhance
import streamlit as st
import openai
import time
import io
from datetime import datetime
import os
import base64
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
import zipfile
import json
import pytz
import requests
import pandas as pd
import numpy as np
import sqlite3

# Inicialización de la API de OpenAI
client = openai
miarchivo = None
mifile = None
#load_dotenv()
try:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID")
    FILE_ID_DB = os.getenv("FILE_ID_DB")
    PROJECT_ID = os.getenv("PROJECT_ID")
    USER = os.getenv("USER")
    PASSWORD = os.getenv("PASSWORD")    
except:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    ASSISTANT_ID = st.secrets["ASSISTANT_ID"]
    FILE_ID_DB = st.secrets["FILE_ID_DB"]
    PROJECT_ID = st.secrets["PROJECT_ID"]
    USER = st.secrets["USER"]
    PASSWORD = st.secrets["PASSWORD"]   

# Método para limpiar el historial del chat y reiniciar la conversación
def limpiar_historial_chat():
    # Mensaje de bienvenida
    msg_bienvenida = "👋 Hola, soy el Asistente IA. Puedo responder a cualquier pregunta que tengas. ¿Te puedo ayudar en algo?"
    
    # Reiniciar el historial del chat con el mensaje de bienvenida
    st.session_state.messages = [{"role": "assistant", "content": msg_bienvenida, "type": "text"}]
    
    # Limpiar el ID del hilo de conversación si existe
    if "thread_id" in st.session_state:
        del st.session_state["thread_id"]

    st.session_state.mostrar_preguntas = False
    # Limpiar el ID del archivo subido si existe
    if "uploaded_files_id" in st.session_state:
        del st.session_state["uploaded_files_id"]

# Inicializar la API de OpenAI, dandole la llave de la API
openai.api_key = OPENAI_API_KEY

st.set_page_config(page_title="Asistente IA UManizales", page_icon="./images/logo.jpeg", layout="centered")

sys.path.insert(0, ".")
from sophisticated_palette.utils import show_palette, model_dict, get_palette, \
    sort_func_dict, store_palette, display_matplotlib_code, display_plotly_code,\
     get_df_rgb, enhancement_range, plot_rgb_3d, plot_hsv_3d, print_praise

gallery_files = glob(os.path.join(".", "images", "*"))
gallery_dict = {image_path.split("/")[-1].split(".")[-2].replace("-", " "): image_path
    for image_path in gallery_files}

st.sidebar.image("./images/2002.i039.010_chatbot_messenger_ai_isometric_set-05.jpg" , use_column_width=True)
st.sidebar.title("Asistente IA UManizales 💬")
st.sidebar.caption("Asistente virtual para analizar los temas principales de los archivos.")

if 'mostrar_preguntas' not in st.session_state:
        st.session_state.mostrar_preguntas = False

# Inicialiar variables de la sesión
if 'uploaded_files_id' not in st.session_state:
    st.session_state.uploaded_files_id = None

if "last_openai_run_state" not in st.session_state:
    st.session_state.last_openai_run_state = None

if 'instructions' not in st.session_state:
    st.session_state.instructions = None

if "openai_model" not in st.session_state:
    st.session_state.openai_model = "gpt-4-1106-preview"

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.sidebar.button('📄 -- Analizador de Documentos PDF -- ', type="primary", use_container_width=True):
        st.session_state.mostrar_preguntas = not st.session_state.mostrar_preguntas

# =======
#   App
# =======

def get_run_id():
    return st.session_state.last_openai_run_state.id

if st.session_state.mostrar_preguntas:
    uploaded_file = st.sidebar.file_uploader("Selecciona un archivo PDF", type="pdf",accept_multiple_files=False)
    if uploaded_file is not None:
        miArchivo = uploaded_file
        file_name = uploaded_file.name
        if st.session_state.uploaded_files_id is None:
            st.success(f"✅ Archivo **{file_name}** seleccionado correctamente.")

# Botón para borrar la conversación
st.sidebar.button('🗑️ -- Borrar conversación --', on_click=limpiar_historial_chat, type="primary", use_container_width=True)

st.session_state.mostrar_chat = True
# Si el botón ha sido presionado
if st.session_state.mostrar_chat:
    if "thread_id" not in st.session_state:
        # Crear un nuevo hilo de conversación solo si no existe
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        
    # Mostrar la interfaz de chat
    # Emojis para el chat
    avatar_asistente = "🤖"  # Emoji para el asistente
    avatar_usuario = "👨🏻‍💻"  # Emoji para el usuario

    # Agregar el mensaje de bienvenida solo la primera vez
    if not st.session_state.messages:
        msg_bienvenida="👋 Hola, soy el Asistente de archivos, puedo ayudarte con información de los archivos PDF. ¿Como puedo ayudarte?"
        st.session_state.messages.append({"role": "assistant", "content": msg_bienvenida, "type": "text"})

    # Mostrar los mensajes existentes en el chat
    for message in st.session_state.messages:
        avatar = avatar_asistente if message["role"] == "assistant" else avatar_usuario
        with st.chat_message(message["role"], avatar=avatar):
            if message["type"] == "text":
                st.markdown(message["content"])
            elif message["type"] == "image":
                file_id = message["file_id"]
                try:
                    # Obtener los bytes de la imagen y crear un objeto Image
                    image_bytes = client.files.content(file_id).content
                    image = Image.open(io.BytesIO(image_bytes))
                    # Mostrar la imagen en Streamlit
                    st.image(image, caption="Imagen generada por el Asistente IA UManizales.")
                except Exception as e:
                    error_message = f"Error al cargar la imagen: {e}"
                    st.markdown(error_message) 
            else:
                try:
                    st.markdown(message["content"])
                except:
                    st.markdown("No fue posible obtener el mensaje")
    
    # Entrada de mensajes del usuario
    try:
        if prompt := st.chat_input("Mensaje"):
            
            # Mostrar el mensaje del usuario en el chat
            st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})
            with st.chat_message("user", avatar=avatar_usuario):
                st.markdown(prompt)
            try:
                
                if st.session_state.uploaded_files_id is None:
                    file = client.files.create(file=miArchivo, purpose='assistants')
                    mifile = file
                    st.session_state.uploaded_files_id = file.id
                    client.beta.assistants.files.create(assistant_id=ASSISTANT_ID, file_id=file.id)
                    
                # Agregar el mensaje del usuario al hilo existente
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content= prompt + " ten en cuenta que te acabo de subir un documento en este hilo de conversación",
                    file_ids=st.session_state.uploaded_files_id) # Ampliar de 1 minuto a 5 minutos para datasets grandes
                 
                # Crear un nuevo run con el modelo y los archivos asociados al asistente
                st.session_state.last_openai_run_state = client.beta.threads.runs.create(
                    thread_id=st.session_state.thread_id,
                    assistant_id=ASSISTANT_ID,
                    instructions=st.session_state.instructions,
                    timeout=5*60)   
            except:
                # Agregar el mensaje del usuario al hilo existente
                client.beta.threads.messages.create(
                    thread_id=st.session_state.thread_id,
                    role="user",
                    content=prompt) # Ampliar de 1 minuto a 5 minutos para datasets grandes
            
                # Crear un nuevo run con el modelo y los archivos asociados al asistente
                st.session_state.last_openai_run_state = client.beta.threads.runs.create(
                    thread_id=st.session_state.thread_id,
                    assistant_id=ASSISTANT_ID,
                    timeout=5*60)            
            
            # Verificar si el run ha sido completado
            completed = False
            while not completed:                
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=get_run_id())    
                if run.status == "requires_action":
                    tools_output = []
                    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                        f = tool_call.function
                        f_name = f.name
                        f_args = json.loads(f.arguments)
                        tool_result = tool_to_function[f_name](**f_args)
                        tools_output.append(
                            {
                                "tool_call_id": tool_call.id,
                                "output": tool_result,
                            }
                        )
                        
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=st.session_state.thread_id,
                        run_id=get_run_id(),
                        tool_outputs=tools_output
                    )

                if run.status == "completed":
                    completed = True

                else:
                    time.sleep(0.2)

            # Recuperar mensajes agregados por el asistente
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id
            )

            # Procesar y mostrar los mensajes del asistente
            assistant_messages_for_run = [
                message for message in messages 
                if message.run_id == run.id and message.role == "assistant"
            ]
            for message in reversed(assistant_messages_for_run):
                
                if message.content[0].type == "text":
                    full_response = message.content[0].text.value 
                    st.session_state.messages.append({"role": "assistant", "content": full_response, "type": "text"})
                    with st.chat_message("assistant", avatar=avatar_asistente):
                        st.markdown(full_response, unsafe_allow_html=True)
                
                if message.content[0].type == "image_file":
                    # Obtener el file_id del mensaje
                    file_id = message.content[0].image_file.file_id

                    # Agregar una referencia a la imagen en el historial del chat
                    st.session_state.messages.append({"role":"assistant", "content": f"Imagen con ID: {file_id}", "type": "image", "file_id": file_id})

                    try:
                        # Obtener los bytes de la imagen y crear un objeto Image
                        image_bytes = client.files.content(file_id).content
                        image = Image.open(io.BytesIO(image_bytes))

                        # Mostrar la imagen en Streamlit
                        with st.chat_message("assistant", avatar=avatar_asistente):
                            st.image(image, caption="Imagen generada por el Asistente IA UManizales")
                    except Exception as e:
                        error_message = f"Error al obtener la imagen: {e}"
                        with st.chat_message("assistant", avatar=avatar_asistente):
                            st.markdown(error_message)
                
                if message.content[0].type != "text" and message.content[0].type != "image_file":
                    response_text = "No se logró una respuesta válida"
                    st.session_state.messages.append({"role": "assistant", "content": response_text, "type": "text"})
                    with st.chat_message("assistant", avatar=avatar_asistente):
                        st.markdown(response_text, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error recibiendo el mensaje: {e}", icon="🚨")
else:
    st.caption("¡Bienvenido! Oprima el botón para tener una conversación con su asistente inteligente. Disponible para responder sus preguntas y proporcionarle información basada en datos.")
    