import streamlit as st
import requests

st.set_page_config(page_title="Consulta Técnica de CAPs", layout="wide")

st.title("Sistema de Consulta Técnica de CAPs")
st.markdown("selecciona el nodo a consultar, el modelo LLM y haz una pregunta para obtener una respuesta.")

# Input de usuario
pregunta = st.text_area("Escribe tu pregunta:", height=100)
modelo = st.selectbox("Selecciona el modelo LLM:", [
    "llama3:8b-instruct-q4_0",
    "zephyr:7b-beta-q4_0",
    "mistral:7b-instruct-v0.3-q4_0",
    "phi3:3.8b-mini-4k-instruct-q4_0",
    "tinyllama:1.1b-chat-v1-q4_0"
])
id_cap = st.selectbox("Selecciona el nodo a consultar:", ["TFMA101", "TFMA102", "TFMA201", "TFMA202", "TFMA203", "TFMB101", "TFMB102", "TFMB103", "TFMB201", "TFMB202"])

if st.button("Consultar"):
    if not pregunta.strip():
        st.warning("Por favor, escribe una pregunta.")
    else:
        with st.spinner("Consultando..."):
            try:
                response = requests.post("http://localhost:8000/consultar", json={
                    "pregunta": pregunta,
                    "modelo": modelo
                })
                if response.status_code == 200:
                    data = response.json()
                    st.subheader("📌 Respuesta del modelo")
                    st.write(data["respuesta"])

                    st.subheader("📚 Fragmentos utilizados")
                    for i, frag in enumerate(data["fragmentos"], 1):
                        st.markdown(f"**Fragmento {i}:**")
                        st.code(frag, language="markdown")
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Error al conectar con la API: {e}")