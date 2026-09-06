# parsers/parse_coordenadas.py
import re
from backend.etl.utils.coord_utils import utm_a_gms
import webbrowser

def extraer_lat_lon(texto):
    matches = re.findall(r'\d{1,3}[^NSEWOnsewo\r\n]{1,20}[NSEWO0nsewo]', texto)
    lat, lon = None, None
    for m in matches:
        m = m.strip().replace('""', '"')
        dir_final = m[-1].upper()

        if dir_final in ['N', 'S'] and lat is None:
            lat = m
        elif dir_final in ['E', 'O', 'W', '0'] and lon is None:
            if dir_final == 'O' or dir_final == '0':
                m = m[:-1] + 'E'
            elif dir_final == 'W':
                m = m[:-1] + 'W'
            lon = m

    return lat, lon

def parsear_coordenadas(texto, abrir_mapa = False):
    texto = texto.replace("\n", " ").replace("  ", " ")
    print(texto)
    resultado = {}

    lat_ocr, lon_ocr = extraer_lat_lon(texto)

    match_x = re.search(r'X[:=]?\s*([\d\.,]+)', texto)
    match_y = re.search(r'Y[:=]?\s*([\d\.,]+)', texto)
    if match_x:
        resultado["UTM_X"] = match_x.group(1).replace(",", ".")
    if match_y:
        resultado["UTM_Y"] = match_y.group(1).replace(",", ".")

    match_huso = re.search(r'HUSO\s*(?:UTM)?[:=]?\s*([0-9]{1,2}[A-Z]?)', texto.upper())
    if match_huso:
        resultado["UTM_HUSO"] = match_huso.group(1).strip()

    match_cota = re.search(r'COTA(?:\s+DE\s+TERRENO)?[:=]?\s*(\d+)', texto, re.IGNORECASE)
    if match_cota:
        resultado["Cota"] = match_cota.group(1) + "m"

    # Verificación cruzada con GMS
    if all(k in resultado for k in ["UTM_X", "UTM_Y", "UTM_HUSO"]):
        lat_gms, lon_gms = utm_a_gms(resultado)
        def direccion(val): return val[-1] if val else None

        # Forzar letra OCR si no coincide
        if lat_gms and lat_ocr and direccion(lat_gms) != direccion(lat_ocr):
            lat_gms = lat_gms[:-1] + direccion(lat_ocr)
            print(lat_gms)
        if lon_gms and lon_ocr and direccion(lon_gms) != direccion(lon_ocr):
            lon_gms = lon_gms[:-1] + direccion(lon_ocr)
            print(lon_gms)

        resultado["Latitud"] = lat_gms
        resultado["Longitud"] = lon_gms

        if abrir_mapa:
            webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={lat_gms},{lon_gms}")


    return resultado
