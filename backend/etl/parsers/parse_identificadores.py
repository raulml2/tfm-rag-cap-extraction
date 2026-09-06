# parsers/parse_identificadores.py
import re


def parsear_identificadores_A(texto):
    resultado = {}
    lineas = [line.strip() for line in texto.strip().split('\n') if line.strip()]
    for i in range(len(lineas) - 1):
        etiqueta = lineas[i].upper()

        if "DIRECCION" in etiqueta:
            resultado["Direccion"] = lineas[i - 1].strip()

        elif "MUNICIPIO" in etiqueta and "PROVINCIA" in etiqueta:
            partes = lineas[i - 1].split()
            resultado["Provincia"] = partes[-1].strip()
            resultado["Municipio"] = " ".join(partes[:-1]).strip()

    match_nodo = re.search(r'([A-Z]{3}\d{4})[-_](\S+)', texto.upper())
    if match_nodo:
        resultado["Nodo"]    = match_nodo.group(1)
        resultado["Cluster"] = match_nodo.group(2)
        
    return resultado


def parsear_identificadores_B(texto):
    resultado = {}
    texto = texto.upper().replace("'", " ").replace("\"", " ")
    texto = texto.replace("  ", " ").replace("\n", " ")

    match_nodo = re.search(r'([A-Z]{3}\d{4})[-_](\S+)', texto.upper())
    if match_nodo:
        resultado["Nodo"]    = match_nodo.group(1)
        resultado["Cluster"] = match_nodo.group(2)

    match_dir = re.search(r'DIRECCION[:\s]+([A-Z0-9\\-\\/., ]{5,50})', texto)
    if match_dir:
        resultado['Direccion'] = match_dir.group().strip()

    match_mun = re.search(r'LOCALIDAD[:\s]+([A-Z ]+)', texto)
    if match_mun:
        resultado['Municipio'] = match_mun.group(1).strip()

    match_prov = re.search(r'PROVINCIA[:\s]+([A-Z ]+)', texto)
    if match_prov:
        resultado['Provincia'] = match_prov.group(1).strip()

    return resultado


def parsear_identificadores_emplazamiento(texto):
    resultado = parsear_identificadores_A(texto)
    claves_clave = ['Direccion', 'Municipio', 'Provincia']

    if not all(k in resultado for k in claves_clave):
        resultado = parsear_identificadores_B(texto)

    return resultado
