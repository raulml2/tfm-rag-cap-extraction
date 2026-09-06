from collections import defaultdict
from typing import List, Dict

def procesar_trabajos(frases: List[str]) -> Dict[str, List[str]]:
    resumen = defaultdict(list)

    verbos = {
        "instalar": ["INSTALAR", "MONTAR", "COLOCAR"],
        "sustituir": ["SUSTITUIR", "CAMBIAR", "REEMPLAZAR"],
        "alimentar": ["ALIMENTAR", "CONECTAR", "ENGANCHAR"],
        "reubicar": ["REUBICAR", "TRASLADAR", "MOVER"],
        "ampliar": ["AMPLIAR", "EXTENDER", "AGRANDAR"],
        "retirar": ["RETIRAR", "QUITAR", "ELIMINAR"],
        "configurar": ["CONFIGURAR", "AJUSTAR", "PARAMETRIZAR"],
        "configuracion": ["SE CONFIGURAN", "AJUSTAR", "PARAMETRIZAR"],
        "conexionado": ["CONEXIONADO", "SE CONECTAN", "SE CONEXIONAN"],
        "mantener": ["SE MANTIENEN", "MANTENER"],
        "incorporar": ["SE AÑADE","AÑADIR","INCORPORAR"],
        "tecnologias": ["TECNOLOGIAS:"],
        "plan": ["PLAN"],
        "otros": []
    }

    for frase in frases:
        frase_mayus = frase.upper()
        mejor_clave = None
        mejor_pos = float('inf')

        for clave, sinonimos in verbos.items():
            for verbo in sinonimos:
                pos = frase_mayus.find(verbo)
                if pos != -1 and pos < mejor_pos:
                    mejor_clave = clave
                    mejor_pos = pos

        if mejor_clave:
            resumen[mejor_clave].append(frase)
        else:
            resumen["otros"].append(frase)

    return dict(resumen)

def segmentar_frases(texto: str) -> List[str]:
    lineas = texto.split('\n')
    frases = []
    frase_actual = ""

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue  # saltar líneas vacías

        if linea.startswith('-'):
            # Guardar la frase anterior antes de empezar una nueva
            if frase_actual:
                frases.append(frase_actual.strip())
            frase_actual = linea[1:].strip()  # quitar el guion inicial
        else:
            if frase_actual and (':' in linea or not linea.startswith('-')):
                frase_actual += ' ' + linea.strip()
            else:
                frases.append(linea)

    # Añadir la última frase si quedó pendiente
    if frase_actual:
        frases.append(frase_actual.strip())

    # Filtrar frases vacías o muy cortas
    return [f for f in frases if len(f) > 5]

def procesar_trabajos_detallado(texto: str) -> Dict[str, List[str]]:
    frases = segmentar_frases(texto)
    return procesar_trabajos(frases)