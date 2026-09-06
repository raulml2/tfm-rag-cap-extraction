from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.rag.consultar_cap import responder_pregunta
from backend.carga_datos import cargar_datos_por_nodo
import traceback

app = FastAPI()

class PreguntaRequest(BaseModel):
    pregunta: str
    modelo: str = "llama3:8b-instruct-q4_0"
    cap: str = "TFMA101"

@app.post("/consultar")
def consultar_pregunta(req: PreguntaRequest):
    try:
        print(req.cap)
        index, docs, embedder, seccion_embeddings = cargar_datos_por_nodo(req.cap)
        respuesta, fragmentos = responder_pregunta(req.pregunta, embedder, seccion_embeddings, index, docs, top_k=4, model=req.modelo)
        return {
            "respuesta": respuesta,
            "fragmentos": [frag["content"] for frag in fragmentos]
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

#  python -m uvicorn backend.api.main:app --reload
# python -m streamlit run frontend/chatbot.py

