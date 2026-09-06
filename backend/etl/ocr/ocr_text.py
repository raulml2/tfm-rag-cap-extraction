# ocr/ocr_text.py
from PIL import Image
import pytesseract

def extraer_texto_ocr_por_zona(page, rect, dpi=300, mostrar_imagen=False):
    """
    Extrae texto de una zona rectangular mediante OCR.
    """
    pix = page.get_pixmap(clip=rect, dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    if mostrar_imagen:
        img.show()

    texto = pytesseract.image_to_string(img, config='--psm 6').strip()
    return texto