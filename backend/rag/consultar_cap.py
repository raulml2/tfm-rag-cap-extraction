# consulta_cap.py
import pickle
import faiss
from sentence_transformers import SentenceTransformer
import requests
import time
import numpy as np
import pandas as pd

# Descripciones semánticas por sección
DESCRIPCIONES_SECCIONES = {
    "emplazamiento": "Ubicación del nodo, dirección, municipio, provincia, coordenadas geográficas, latitud, longitud, cota.",
    "consumos": "Consumo eléctrico actual y reformado, consumo total, consumo por componente como eq_radio, tx, bbu, rru.",
    "hardware": "Modelos y cantidades de antenas, RRUs, BBUs, conectores, tipo de hardware instalado.",
    "prl": "Prevención de riesgos laborales (PRL), accesos a las antenas, medidas y sistemas de seguridad",
    "antenas_sector": "Sectores del nodo, distribución de antenas por sector, modelos predominantes, tecnologías, orientaciones.",
    "tareas": "Tareas del operador y propietario, responsabilidades, mantenimiento, configuración, instalación."
}

def detectar_seccion_relevante(pregunta, embedder, seccion_embeddings, verbose=True):
    pregunta_emb = embedder.encode([pregunta], normalize_embeddings=True)
    similitudes = np.dot(seccion_embeddings, pregunta_emb.T).squeeze()
    secciones = list(DESCRIPCIONES_SECCIONES.keys())
    idx_max = np.argmax(similitudes)
    seccion = secciones[idx_max]
    
    if verbose:
        print("Similitudes por sección:")
        for sec, sim in zip(secciones, similitudes):
            print(f"  {sec}: {sim:.3f}")
    
    return seccion if similitudes[idx_max] > 0.4 else None  # Umbral ajustable

def buscar_similares(query, embedder, index, docs, top_k=3):
    query_emb = embedder.encode([query]).astype("float32")
    if isinstance(index, faiss.Index):
        # Búsqueda en índice completo
        D, I = index.search(query_emb, top_k)
        resultados = [docs[idx] for idx in I[0] if idx < len(docs)]
    else:
        # Búsqueda en subconjunto (sin FAISS)
        docs_texts = [doc['content'] for doc in docs]
        doc_embs = embedder.encode(docs_texts).astype("float32")
        sims = np.dot(doc_embs, query_emb.T).squeeze()
        top_indices = sims.argsort()[::-1][:top_k]
        resultados = [docs[i] for i in top_indices]
    return resultados

def filtrar_docs_por_seccion(docs, seccion_objetivo):
    return [doc for doc in docs if doc['metadata'].get('section', '') == seccion_objetivo]

def eliminar_fragmentos_duplicados(docs):
    vistos = set()
    unicos = []
    for doc in docs:
        content = doc["content"].strip()
        if content not in vistos:
            vistos.add(content)
            unicos.append(doc)
    return unicos

def construir_prompt_rag(context_chunks, pregunta):
    contexto = "\n\n".join([f"Fragmento {i+1}: {chunk}" for i, chunk in enumerate(context_chunks)])
    prompt = ("""
        Eres un ingeniero de telecomunicaciones experto en diseño radio con más de 25 años de experiencia. 
        Responde en español de forma clara y concisa a la siguiente pregunta SOLO usando la información de los  
        fragmentos proporcionados. Si la información no está en los fragmentos, responde 'No se encuentra información suficiente'.\n\n"""
        f"{contexto}\n\n"
        f"Pregunta: {pregunta}\n"
        "Respuesta:"
    )
    return prompt 

def generar_respuesta(prompt, model="llama3:8b-instruct-q4_0"):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    )
    print("Respuesta bruta del modelo:", response.json())  # Agregado para depuración

    data = response.json()
    if "response" not in data:
        raise ValueError(f"La respuesta del modelo no contiene la clave 'response': {data}")

    return data["response"]

def responder_pregunta(query, embedder, seccion_embeddings, index, docs, top_k=3, model="llama3:8b-instruct-q4_0"):
    print(f"\nPregunta recibida: {query}")
    
    seccion_relevante = detectar_seccion_relevante(query, embedder, seccion_embeddings)
    
    if seccion_relevante:
        print(f"Sección detectada: {seccion_relevante}")
        docs_filtrados = filtrar_docs_por_seccion(docs, seccion_relevante)
        print(f"Documentos filtrados por sección: {len(docs_filtrados)}")

        if len(docs_filtrados) > 0:
            docs_para_contexto = buscar_similares(query, embedder, None, docs_filtrados, top_k=top_k)
        else:
            print("No se encontraron documentos en la sección. Usando búsqueda general.")
            docs_para_contexto = buscar_similares(query, embedder, index, docs, top_k=top_k)
    else:
        print("No se detectó una sección relevante con suficiente confianza.")
        docs_para_contexto = buscar_similares(query, embedder, index, docs, top_k=top_k)

    print(f"Fragmentos recuperados antes de eliminar duplicados: {len(docs_para_contexto)}")
    docs_para_contexto = eliminar_fragmentos_duplicados(docs_para_contexto)
    print(f"Fragmentos únicos tras eliminar duplicados: {len(docs_para_contexto)}")

    context_chunks = [doc['content'] for doc in docs_para_contexto]
    if not context_chunks:
        print("No se encontraron fragmentos relevantes para construir el contexto.")
    else:
        print("Fragmentos utilizados en el prompt:")
        for i, frag in enumerate(context_chunks, 1):
            print(f"  Fragmento {i}: {frag[:100]}...")  # Mostrar solo los primeros 100 caracteres

    prompt = construir_prompt_rag(context_chunks, query)
    print("Prompt construido correctamente. Enviando al modelo...")

    respuesta = generar_respuesta(prompt, model)
    print("Respuesta generada por el modelo.")

    return respuesta, docs_para_contexto



if __name__ == "__main__":
    # Lista de modelos a evaluar
    modelos = [
        "phi3:3.8b-mini-4k-instruct-q4_0",
        "tinyllama:1.1b-chat-v1-q4_0",
        "mistral:7b-instruct-v0.3-q4_0",
        "llama3:8b-instruct-q4_0",
        "zephyr:7b-beta-q4_0"
    ]

    # Lista de preguntas por bloque del JSON
    preguntas = [
        "¿En qué municipio y provincia se encuentra ubicado el nodo, y cuál es su latitud y longitud?",
        "¿Cuál es el consumo eléctrico total previsto tras la reforma y cuál es el consumo de eq._radio en ese escenario?",
        "¿Qué modelos de antena y de RRU se van a instalar en el nodo?",
        "¿Cómo se accede a las antenas desde el punto de vista de PRL y qué sistemas de seguridad existen para ellas?",
        "¿Cuántos sectores tiene el nodo y qué modelos de antenas predominan en cada sector?",
        "Resume las tareas principales que debe realizar el operador y menciona al menos una acción que corresponde al propietario."
    ]

    # Lista para almacenar los resultados
    resultados = []
    index = faiss.read_index("data/index/TFMA101.faiss")
    with open("data/index/TFMA101.pkl", "rb") as f:
        docs = pickle.load(f)
    embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    # Codificar descripciones de secciones una sola vez
    seccion_embeddings = embedder.encode(list(DESCRIPCIONES_SECCIONES.values()), normalize_embeddings=True)

    # Iterar sobre cada modelo y cada pregunta
    for modelo in modelos:
        for pregunta in preguntas:
            print(f"Evaluando modelo: {modelo} | Pregunta: {pregunta}")
            start_time = time.time()
            respuesta, fragmentos = responder_pregunta(pregunta, embedder, seccion_embeddings, index, docs, top_k=4, model=modelo)
            latencia = time.time() - start_time
            resultados.append({
                "modelo": modelo,
                "pregunta": pregunta,
                "respuesta": respuesta,
                "fragmentos_utilizados": "\n---\n".join([f['content'] for f in fragmentos]),
                "latencia": latencia
            })

    # Crear un DataFrame y exportar a Excel
    df = pd.DataFrame(resultados)
    df.to_excel("evaluacion_modelos_llm.xlsx", index=False)
    print("✅ Evaluación completada. Resultados guardados en 'evaluacion_modelos_llm.xlsx'.")