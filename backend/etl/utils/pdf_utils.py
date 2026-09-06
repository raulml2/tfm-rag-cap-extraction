# modules/pdf_utils.py
import pdfplumber
from backend.etl.ocr.ocr_text import extraer_texto_ocr_por_zona

def encontrar_pagina_por_titulo(doc, rect, titulos_esperados, mostrar_imagen=False):
    """
    Busca en el documento la primera página cuyo título (extraído por OCR) coincida con alguno de los esperados.
    """
    for i, page in enumerate(doc):
        titulo = extraer_texto_ocr_por_zona(page, rect, mostrar_imagen=mostrar_imagen)
        titulo = " ".join(titulo.strip().split())
        print(titulo)
        if any(p in titulo.upper() for p in titulos_esperados):
            return i
    return None

def extraer_tablas_de_pagina(pdf_path, pagina_idx):
    """
    Extrae tablas usando pdfplumber desde la página indicada.
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[pagina_idx]
        tablas = page.extract_tables()
    return tablas
