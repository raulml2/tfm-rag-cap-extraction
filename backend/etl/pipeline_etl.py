# pipeline_etl.py
import json
import logging
from pathlib import Path
import argparse
from backend.etl.cap_extractor import CAPExtractor
from backend.etl.normalizar_json import normalizar_y_reestructurar_json_cap
from backend.etl.anon import anonimizar_json

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def cargar_config(path="config/config.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def extraer_datos(pdf_path: Path, config: dict) -> dict:
    extractor = CAPExtractor(str(pdf_path), config)
    extractor.procesar()
    return extractor.resultado

def normalizar_datos(resultado: dict) -> dict:
    return normalizar_y_reestructurar_json_cap(resultado)

def anonimizar_datos(datos: dict, id_cap) -> dict:
    return anonimizar_json(datos,id_cap)

def guardar_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def procesar_cap(id_cap: str, config: dict):
    pdf_path = Path("data/raw") / f"{id_cap}.pdf"
    json_path = Path("data/processed") / f"{id_cap}.json"
    anon_path = Path("data/final") / f"{id_cap}_anon.json"

    if not pdf_path.exists():
        logging.error(f"No se encuentra el archivo PDF: {pdf_path}")
        return

    logging.info(f"Procesando CAP: {id_cap}")

    datos = extraer_datos(pdf_path, config)
    normalizado = normalizar_datos(datos)
    guardar_json(normalizado, json_path)
    logging.info(f"Guardado JSON normalizado en: {json_path}")

    anon = anonimizar_datos(normalizado, id_cap)
    guardar_json(anon, anon_path)
    logging.info(f"Guardado JSON anonimizado en: {anon_path}")

def main():
    parser = argparse.ArgumentParser(description="Extrae y transforma un documento CAP en un JSON estructurado.")
    parser.add_argument("id_cap", help="Ej: CAP_TFMA101")
    args = parser.parse_args()

    config = cargar_config()
    procesar_cap(args.id_cap, config)

if __name__ == "__main__":
    main()



