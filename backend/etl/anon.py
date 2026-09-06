# anon_json.py
import copy, re, random
from typing import Dict, Any

REGEX_REPL = [
    (r"\bTOTEM\b",   "PROPIETARIO"),
    (r"\bCELLNEX\b", "PROPIETARIO"),
    (r"\bORANGE\b",  "CLIENTE"),
]

def anonimizar_json(data: Dict[str, Any], id_cap, verbose: bool = False) -> Dict[str, Any]:
    anon = copy.deepcopy(data)

    # --- Sustitución fija y pseudorrealista ---
    empl = anon.get("emplazamiento", {})
    empl["Nodo"] = id_cap
    empl["Cluster"] = "MUIT2025"
    empl["Direccion"] = "Camino de Vera, 25"
    empl["Municipio"] = "ALGIROS"
    empl["Provincia"] = "VALENCIA"
    empl["Latitud"] = "39°28'51.96 N"
    empl["Longitud"] = "0°20'24.00 W"
    anon["emplazamiento"] = empl

    # --- Regex y NER en texto libre ---
    tareas = anon.get("tareas", {})
    for k, info in tareas.items():
        text = info.get("texto")
        if not text:
            continue
        for pattern, repl in REGEX_REPL:
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        info["texto"] = text

    return anon