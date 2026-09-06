import faiss
import pickle
import os
from sentence_transformers import SentenceTransformer

# Descripciones semánticas por sección
DESCRIPCIONES_SECCIONES = {
    "emplazamiento": "Ubicación del nodo, dirección, municipio, provincia, coordenadas geográficas, latitud, longitud, cota.",
    "consumos": "Consumo eléctrico actual y reformado, consumo total, consumo por componente como eq_radio, tx, bbu, rru.",
    "hardware": "Modelos y cantidades de antenas, RRUs, BBUs, conectores, tipo de hardware instalado.",
    "prl": "Prevención de riesgos laborales (PRL), accesos a las antenas, medidas y sistemas de seguridad",
    "antenas_sector": "Sectores del nodo, distribución de antenas por sector, modelos predominantes, tecnologías, orientaciones.",
    "tareas": "Tareas del operador y propietario, responsabilidades, mantenimiento, configuración, instalación."
}

def cargar_datos_por_nodo(id_cap):
    try:
        index_path = f"data/index/{id_cap}.faiss"
        docs_path = f"data/index/{id_cap}.pkl"

        if not os.path.exists(index_path):
            raise FileNotFoundError(f"No se encontró el índice FAISS: {index_path}")
        if not os.path.exists(docs_path):
            raise FileNotFoundError(f"No se encontró el archivo de documentos: {docs_path}")

        index = faiss.read_index(index_path)

        with open(docs_path, "rb") as f:
            docs = pickle.load(f)

        embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        seccion_embeddings = embedder.encode(list(DESCRIPCIONES_SECCIONES.values()), normalize_embeddings=True)

        return index, docs, embedder, seccion_embeddings

    except Exception as e:
        raise RuntimeError(f"Error al cargar datos para el CAP {id_cap}: {str(e)}")
