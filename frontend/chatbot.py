import streamlit as st
import requests
import time

# Lista de nodos disponibles
NODOS_DISPONIBLES = [
    "TFMA101", "TFMA102", "TFMA201", "TFMA202", "TFMA203",
    "TFMB101", "TFMB102", "TFMB103", "TFMB201", "TFMB202"
]

st.set_page_config(page_title="CAP Bot")

# Inicializar el estado de la sesión
if "nodo" not in st.session_state:
    st.session_state.nodo = None
if "chat" not in st.session_state:
    st.session_state.chat = []

# Título de la app
st.title("🤖 CAP Bot")

# Paso 1: Selección del nodo
if st.session_state.nodo is None:
    # Mensaje de bienvenida
    st.markdown("¡Bienvenido! Soy tu asistente para consultar información técnica de nodos de telecomunicaciones.")
    nodo_input = st.text_input("🔍 Introduce el nodo a consultar (por ejemplo: TFMA101):")
    if nodo_input:
        nodo_input = nodo_input.strip().upper()
        if nodo_input in NODOS_DISPONIBLES:
            st.session_state.nodo = nodo_input
            st.success(f"Nodo {nodo_input} encontrado, abriendo chat de consulta. Por favor, espere unos segundos.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Nodo no encontrado. Por favor, prueba con otro.")
else:
    # Mensaje de bienvenida
    st.markdown(f"Chat de consulta para el nodo {st.session_state.nodo}")
    # Entrada de nueva pregunta
    pregunta = st.chat_input("Escribe tu pregunta...")
    if pregunta:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        try:
            response = requests.post(
                "http://localhost:8000/consultar",
                json={"pregunta": pregunta, "modelo": "llama3:8b-instruct-q4_0", "nodo": st.session_state.nodo}
            )
            if response.status_code == 200:
                data = response.json()
                respuesta = data["respuesta"]
                st.session_state.chat.append({"role": "assistant", "content": respuesta})
            else:
                error_msg = f"Error al consultar la API: {response.status_code}"
                st.session_state.chat.append({"role": "assistant", "content": error_msg})
        except Exception as e:
            error_msg = f"No se pudo conectar con la API: {e}"
            st.session_state.chat.append({"role": "assistant", "content": error_msg})

    # Mostrar historial de conversación solo si hay preguntas
    if st.session_state.chat:
        st.markdown("---")
        for entrada in st.session_state.chat:
            with st.chat_message(entrada["role"]):
                st.markdown(entrada["content"])
