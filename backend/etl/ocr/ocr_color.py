# modules/ocr_color.py
import numpy as np
import cv2
import pytesseract
from pdf2image import convert_from_path

def buscar_trabajos_por_color(pdf_path, empresa, rangos_hsv, dpi=300):
    """
    Busca bloques de color en el PDF asociados a trabajos por empresa.
    Retorna texto OCR si encuentra la sección.
    """
    empresa = empresa.lower()
    imagenes = convert_from_path(pdf_path, dpi=dpi)
    if not imagenes:
        return None

    if empresa not in rangos_hsv:
        raise ValueError("Empresa no reconocida")

    lower = np.array(rangos_hsv[empresa]['lower'])
    upper = np.array(rangos_hsv[empresa]['upper'])

    for i, img_pil in enumerate(imagenes):
        img = np.array(img_pil.convert('RGB'))
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        mascara = cv2.inRange(hsv, lower, upper)
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contornos:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50 and h > 15:
                zona = img[y:y+h, x:x+w]
                texto = pytesseract.image_to_string(zona, config='--psm 6').strip()
                if any(kw in texto.upper() for kw in ["TRABAJOS A REALIZAR", "TAREAS A REALIZAR"]) and len(texto) > 50:
                    return {"pagina": i, "texto": texto}

    return None
