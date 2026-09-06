# utils/normalizar_json.py
import re
import copy
from collections import defaultdict

def normalizar_consumos(consumos_raw):
    resultado = {
        "actual": {"total": None, "detalle": {}, "tecnologias": []},
        "reformado": {"total": None, "detalle": {}, "tecnologias": []}
    }

    def limpiar_valor(v):
        if isinstance(v, str):
            v = v.replace("W", "").replace("--", "0").strip()
        try:
            return float(v)
        except:
            return 0.0

    def parse_tecnologias(data):
        techs = data.get("TECNOLOGIAS\nEXISTENTES", "")
        techs = techs.replace("\n", " ").replace(",", " ")
        techs = re.split(r"[+\-/]", techs)
        techs = [t.strip().replace("OSP", "").replace("VDF", "") for t in techs if t.strip()]
        return sorted(set(techs))

    # Tipo A1: tiene claves "ACTUAL (W)" y "FINAL (W)"
    if any("ACTUAL (W)" in v for v in consumos_raw.values() if isinstance(v, dict)):
        for k, bloque in consumos_raw.items():
            if not isinstance(bloque, dict):
                continue
            clave_norm = k.lower().replace(" ", "_")
            if clave_norm == "total":
                resultado["actual"]["total"] = limpiar_valor(bloque.get("ACTUAL (W)", 0))
                resultado["reformado"]["total"] = limpiar_valor(bloque.get("FINAL (W)", 0))
            else:
                resultado["actual"]["detalle"][clave_norm] = limpiar_valor(bloque.get("ACTUAL (W)", 0))
                resultado["reformado"]["detalle"][clave_norm] = limpiar_valor(bloque.get("FINAL (W)", 0))

    # Tipo A2: contiene "Actual" y "Reformado" como claves principales
    elif "Actual" in consumos_raw:
        actual = consumos_raw.get("Actual", {})
        reformado = consumos_raw.get("Reformado", {})
        resultado["actual"]["total"] = limpiar_valor(actual.get("CONSUMO", 0))
        resultado["reformado"]["total"] = limpiar_valor(reformado.get("CONSUMO", 0))
        resultado["actual"]["tecnologias"] = parse_tecnologias(actual)
        resultado["reformado"]["tecnologias"] = parse_tecnologias(reformado)

    # Tipo A3: formato simple con clave "ESTADO" y "CONSUMO"
    elif all(isinstance(v, dict) and "CONSUMO" in v for v in consumos_raw.values()):
        for estado, bloque in consumos_raw.items():
            estado_norm = estado.strip().lower()
            if "actual" in estado_norm:
                resultado["actual"]["total"] = limpiar_valor(bloque.get("CONSUMO", 0))
            elif "reformado" in estado_norm:
                resultado["reformado"]["total"] = limpiar_valor(bloque.get("CONSUMO", 0))

    return resultado

def normalizar_hardware(hardware_raw):
    hw = {
        "antenas": [],
        "rru": [],
        "bbu": None,
        "conectividad": hardware_raw.get("conectividad", []),
        "infraestructura": hardware_raw.get("infraestructura", {})
    }

    # Unificar clave 'antena' y 'antenas'
    antenas = hardware_raw.get("antenas") or hardware_raw.get("antena") or []
    for ant in antenas:
        hw["antenas"].append({
            "modelo": ant.get("MODELO") or ant.get("modelo"),
            "tipo_conector": ant.get("TIPOCONECTOR", "Desconocido"),
            "cantidad": ant.get("cantidad", 1)
        })

    # Normalizar RRU
    for r in hardware_raw.get("rru", []):
        modelo = r.get("MODELO") or r.get("modelo")
        if not modelo.startswith("RRU"):
            modelo = f"RRU {modelo}"
        hw["rru"].append({
            "modelo": modelo,
            "tipo_conector": r.get("TIPOCONECTOR", "Desconocido"),
            "tecnologias": r.get("tecnologias", [])
        })

    # BBU
    if hardware_raw.get("bbu"):
        hw["bbu"] = hardware_raw["bbu"]

    return hw

def normalizar_antenas(antenas_raw):
    def extraer_cantidad(valor):
        if isinstance(valor, str):
            valor = valor.strip()
            if valor.isdigit():
                return int(valor)
            if "x" in valor:
                try:
                    return int(valor.lower().split("x")[0].strip())
                except:
                    return 1
        try:
            return int(valor)
        except:
            return 1

    def procesar_antena(ant):
        def extraer_longitud(valor):
            if isinstance(valor, dict):
                return valor.get("valor")
            if isinstance(valor, str):
                partes = valor.lower().replace("mm", "").replace("m", "").split("x")
                try:
                    return float(partes[-1])
                except:
                    return None
            return None

        modelo = ant.get("MODELO") or ant.get("TIPO_ANTENA")
        tipo = "Activa" if (modelo and "AAU" in modelo) or ant.get("COAX_N") in ["", None, 0] else "Pasiva"
        altura = ant.get("SUELO") or ant.get("ALTURA_TOP_ANT") or ant.get("CUBIERTA")

        return {
            "modelo": modelo,
            "tipo": tipo,
            "orientacion": ant.get("AZIMUT") or ant.get("ORIENTACION"),
            "altura_top": altura,
            "edt": ant.get("EDT"),
            "coax": {
                "cantidad": extraer_cantidad(ant.get("COAX_N")) if "COAX_N" in ant else extraer_cantidad(ant.get("COAX_NTIPO", ant.get("TIPO", ""))),
                "tipo": ant.get("COAX_TIPO") or ant.get("TIPO") or ant.get("COAX_NTIPO", "").replace("\"", ""),
                "longitud": extraer_longitud(ant.get("COAX_LONG") or ant.get("LONG"))
            },
            "fo": {
                "cantidad": extraer_cantidad(ant.get("FO_N")) if "FO_N" in ant else extraer_cantidad(ant.get("FO_LONG")),
                "longitud": extraer_longitud(ant.get("FO_LONG") or ant.get("F.O. LONG"))
            },
            "vcc": {
                "cantidad": extraer_cantidad(ant.get("VCC_N")) if "VCC_N" in ant else 1,
                "longitud": extraer_longitud(ant.get("VCC_LONG") or ant.get("CC. LONG"))
            }
        }

    resultado = {}
    for sector, antenas in antenas_raw.items():
        agrupadas = defaultdict(lambda: {"tecnologias": []})

        for ant in antenas if isinstance(antenas, list) else list(antenas.values()):
            clave = (
                ant.get("TIPO_ANTENA") or ant.get("MODELO"),
                ant.get("ORIENTACION") or ant.get("AZIMUT"),
                ant.get("ALTURA_TOP_ANT") or ant.get("SUELO") or ant.get("CUBIERTA"),
                ant.get("EDT"),
                ant.get("COAX_NTIPO") or ant.get("TIPO"),
                ant.get("COAX_LONG"),
                ant.get("FO_LONG"),
                ant.get("VCC_LONG")
            )
            antena_proc = procesar_antena(ant)
            agrupadas[clave].update(antena_proc)
            tecnologia = ant.get("TECNOLOGIA") or ant.get("TECNOLOGIAS")
            if isinstance(tecnologia, str):
                techs = [t.strip().replace("OSP", "").replace("VDF", "") for t in re.split(r"[,+/]", tecnologia) if len(t.strip()) > 1]
            elif isinstance(tecnologia, list):
                techs = [t.strip().replace("OSP", "").replace("VDF", "") for t in tecnologia]
            else:
                techs = []
            agrupadas[clave]["tecnologias"].extend([t for t in techs if t])

        for k in agrupadas:
            agrupadas[k]["tecnologias"] = sorted(set(agrupadas[k]["tecnologias"]))

        resultado[sector.upper()] = list(agrupadas.values())

    return resultado

def normalizar_prl(prl_raw):
    def limpiar(dic):
        return {
            "ubicacion": dic.get("UBICACION", []),
            "acceso": dic.get("ACCESO ANTENAS", dic.get("ACCESO BTS", [])),
            "seguridad": dic.get("SEGURIDAD", [])
        }

    return {
        "antenas": limpiar(prl_raw.get("antenas", {})),
        "equipos": limpiar(prl_raw.get("equipos", {}))
    }

def normalizar_y_reestructurar_json_cap(json_dict):
    data = copy.deepcopy(json_dict)

    # 1. Limpiar coordenadas
    if "emplazamiento" in data:
        for campo in ["Latitud", "Longitud"]:
            if campo in data.get("emplazamiento", {}):
                valor = data["emplazamiento"][campo]
                data["emplazamiento"][campo] = valor.replace(" ", "").replace("\"", "")

    # 2. Limpiar y normalizar calculos
    if "calculos" in data:
        # Normalizar Potencia
        raw_consumos = data.get("calculos", {}).get("consumos", {})
        data["calculos"]["consumo"] = normalizar_consumos(raw_consumos)
        data["calculos"].pop("consumos", None)
        # Normalizar Hardware
        data["calculos"]["hardware"] = normalizar_hardware(data["calculos"].get("hardware", {}))
        # Normalizar Antenas y Sectores
        data["calculos"]["antenas"] = normalizar_antenas(data["calculos"].get("antenas", {}))

    # 3. Limpiar y normalizar PRL
    if "prl" in data:
        data["prl"] = normalizar_prl(data["prl"])
    
    # 4. Eliminar claves vacías
    def limpiar_diccionario(d):
        if isinstance(d, dict):
            return {k: limpiar_diccionario(v) for k, v in d.items() if v not in [None, "", [], {}]}
        elif isinstance(d, list):
            return [limpiar_diccionario(i) for i in d if i not in [None, "", [], {}]]
        return d

    return limpiar_diccionario(data)
