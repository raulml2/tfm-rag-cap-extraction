# indexar_cap.py
import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def cargar_json(ruta):
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)

def resumen_antenas_sector(sector, lista_antenas):
    modelos = set()
    tecnologias = set()
    orientaciones = set()
    alturas = set()
    for ant in lista_antenas:
        if ant.get("modelo"):
            modelos.add(ant["modelo"])
        for t in ant.get("tecnologias", []):
            tecnologias.add(t.strip())
        if ant.get("orientacion"):
            orientaciones.add(ant["orientacion"])
        if ant.get("altura_top"):
            alturas.add(ant["altura_top"])
    resumen = (
        f"En el {sector} hay {len(lista_antenas)} antenas instaladas. "
        f"Modelos: {', '.join(modelos)}. "
        f"Tecnologías soportadas: {', '.join(tecnologias)}. "
        f"Orientaciones: {', '.join(orientaciones)}. "
        f"Alturas top: {', '.join(alturas)}."
    )
    return resumen

def resumen_antenas_global(antenas_por_sector):
    total_antenas = 0
    sectores = []
    modelos = set()
    tecnologias = set()
    orientaciones = set()
    alturas = set()
    for sector, lista_antenas in antenas_por_sector.items():
        sectores.append(sector)
        total_antenas += len(lista_antenas)
        for ant in lista_antenas:
            if ant.get("modelo"):
                modelos.add(ant["modelo"])
            for t in ant.get("tecnologias", []):
                tecnologias.add(t.strip())
            if ant.get("orientacion"):
                orientaciones.add(ant["orientacion"])
            if ant.get("altura_top"):
                alturas.add(ant["altura_top"])
    resumen = (
        f"El nodo cuenta con {total_antenas} antenas distribuidas en {len(sectores)} sectores: {', '.join(sectores)}. "
        f"Modelos instalados: {', '.join(modelos)}. "
        f"Tecnologías soportadas: {', '.join(tecnologias)}. "
        f"Orientaciones presentes: {', '.join(orientaciones)}. "
        f"Alturas top: {', '.join(alturas)}."
    )
    return resumen

def resumen_prl(prl_dict):
    def frase(tipo, campos):
        partes = []
        if "ubicacion" in campos and campos["ubicacion"]:
            ubic = ", ".join(campos["ubicacion"])
            partes.append(f"están ubicadas en {ubic.lower()}")
        if "acceso" in campos and campos["acceso"]:
            acc = ", ".join(campos["acceso"])
            partes.append(f"se accede por {acc.lower()}")
        if "seguridad" in campos and campos["seguridad"]:
            seg = ", ".join(campos["seguridad"])
            partes.append(f"y cuentan con {seg.lower()} como medidas de seguridad")
        if partes:
            return f"Las {tipo} {', '.join(partes)}."
        else:
            return ""    
    resumenes = []
    for tipo in ["antenas", "equipos"]:
        if tipo in prl_dict:
            resumen = frase(tipo, prl_dict[tipo])
            if resumen:
                resumenes.append(resumen)
    return " ".join(resumenes)

def resumen_narrativo_tareas(actor, resumen_dict):
    """Crea un texto narrativo concatenando todas las tareas resumen de un actor."""
    frases = []
    for categoria, lista in resumen_dict.items():
        if lista:
            categoria_txt = categoria.replace("_", " ").capitalize()
            for tarea in lista:
                frases.append(f"{categoria_txt}: {tarea.strip()}")
    if frases:
        joined = " ".join(frases)
        return f"Resumen de las tareas principales que debe realizar el {actor}: {joined}"
    return None

def json_a_docs(cap_json):
    docs = []
    # 1. Emplazamiento
    empl = cap_json.get("emplazamiento", {})
    empl_texto = (
        f"El nodo identificado como {empl.get('Nodo', 'N/A')} pertenece al cluster {empl.get('Cluster', 'N/A')}. "
        f"Se encuentra ubicado en {empl.get('Direccion', 'N/A')}, municipio {empl.get('Municipio', 'N/A')}, provincia {empl.get('Provincia', 'N/A')}. "
        f"Sus coordenadas geográficas son: {empl.get('Latitud', 'N/A')} {empl.get('Longitud', 'N/A')}. Presenta una cota de {empl.get('Cota', 'N/A')}"
    )
    docs.append({"content": empl_texto, "metadata": {"section": "emplazamiento"}})
    
    # 2. CALCULOS
    calc = cap_json.get("calculos", {})

    # 2.1 CONSUMOS
    consumos = calc.get("consumo", {})
    for tipo in ["actual", "reformado"]:
        bloque = consumos.get(tipo, {})
        total = bloque.get("total")
        detalle = bloque.get("detalle", {})
        # Documento: consumo total
        if total is not None:
            texto = (
                f"El consumo total {'actual' if tipo == 'actual' else 'previsto tras la reforma'} "
                f"es de {total} W."
            )
            docs.append({
                "content": texto,
                "metadata": {"section": "consumos", "tipo": tipo, "campo": "total"}
            })
        # Documento: detalle de cada componente
        for componente, valor in detalle.items():
            texto = (
                f"El consumo de '{componente}' "
                f"{'actual' if tipo == 'actual' else 'previsto tras la reforma'} "
                f"es de {valor} W."
            )
            docs.append({
                "content": texto,
                "metadata": {
                    "section": "consumos",
                    "tipo": tipo,
                    "campo": componente
                }
            })
        # Documento: Resumen consumos
        for tipo in ["actual", "reformado"]:
            bloque = consumos.get(tipo, {})
            detalle = bloque.get("detalle", {})
            if detalle:
                detalle_txt = "; ".join(
                    [f"{k}: {v} W" for k, v in detalle.items()]
                )
                texto = (
                    f"El desglose de consumo "
                    f"{'actual' if tipo == 'actual' else 'previsto tras la reforma'} es: {detalle_txt}."
                )
                docs.append({
                    "content": texto,
                    "metadata": {"section": "consumos", "tipo": tipo, "campo": "resumen"}
                })

    # 2.2. HARDWARE
    hardware = calc.get("hardware", {})

    # Antenas
    for ant in hardware.get("antenas", []):
        texto = (
            f"Antena modelo {ant.get('modelo', 'N/A')}, "
            f"cantidad: {ant.get('cantidad', 'N/A')}"
        )
        if ant.get("tipo_conector"):
            texto += f", tipo de conector: {ant['tipo_conector']}"
        texto += "."
        docs.append({
            "content": texto,
            "metadata": {
                "section": "hardware",
                "tipo_hw": "antena",
                "modelo": ant.get('modelo'),
                "tipo_conector": ant.get('tipo_conector', None)
            }
        })

    # RRU
    for rru in hardware.get("rru", []):
        texto = (
            f"RRU modelo {rru.get('modelo', 'N/A')}"
        )
        if rru.get("tipo_conector"):
            texto += f", tipo de conector: {rru['tipo_conector']}"
        texto += "."
        docs.append({
            "content": texto,
            "metadata": {
                "section": "hardware",
                "tipo_hw": "rru",
                "modelo": rru.get('modelo'),
                "tipo_conector": rru.get('tipo_conector', None)
            }
        })

    # BBU
    for bbu in hardware.get("bbu", []):
        texto = (
            f"BBU modelo {bbu.get('modelo', 'N/A')}, cantidad: {bbu.get('cantidad', 'N/A')}."
        )
        docs.append({
            "content": texto,
            "metadata": {
                "section": "hardware",
                "tipo_hw": "bbu",
                "modelo": bbu.get('modelo')
            }
        })

    # RESUMEN HARDWARE
    antenas = hardware.get("antenas", [])
    rrus = hardware.get("rru", [])
    bbus = hardware.get("bbu", [])
    # Modelos únicos y conteos
    modelos_antenas = list({ant.get('modelo', 'N/A') for ant in antenas})
    modelos_rrus = list({rru.get('modelo', 'N/A') for rru in rrus})
    modelos_bbus = list({bbu.get('modelo', 'N/A') for bbu in bbus})
    resumen = (
        f"El nodo dispone de {len(antenas)} antenas (modelos: {', '.join(modelos_antenas)}), "
        f"{len(rrus)} RRUs (modelos: {', '.join(modelos_rrus)}) y "
        f"{len(bbus)} BBUs (modelos: {', '.join(modelos_bbus)})."
    )
    docs.append({
        "content": resumen,
        "metadata": {"section": "hardware", "tipo_hw": "resumen_global"}
    })
    
    # 2.3 SECTORES
    antenas_por_sector = calc.get("antenas", {})
    for sector, lista_antenas in antenas_por_sector.items():
        for i, ant in enumerate(lista_antenas, 1):
            tecnologias = ', '.join([tec.strip() for tec in ant.get('tecnologias', [])])
            coax = ant.get('coax', {})
            fo = ant.get('fo', {})
            vcc = ant.get('vcc', {})

            texto = (
                f"En el {sector}, antena {i}: modelo {ant.get('modelo', 'N/A')}, tipo {ant.get('tipo', 'N/A')}, "
                f"tecnologías: {tecnologias}, orientación: {ant.get('orientacion', 'N/A')}, "
                f"altura top: {ant.get('altura_top', 'N/A')}, EDT: {ant.get('edt', 'N/A')}. "
                f"Coax: {coax.get('cantidad', 'N/A')} x {coax.get('tipo', 'N/A')}, {coax.get('longitud', 'N/A')} m. "
                f"FO: {fo.get('cantidad', 'N/A')} x {fo.get('longitud', 'N/A')} m. "
                f"VCC: {vcc.get('cantidad', 'N/A')} x {vcc.get('longitud', 'N/A')} m."
            )
            docs.append({
                "content": texto,
                "metadata": {
                    "section": "antenas_sector",
                    "sector": sector,
                    "modelo": ant.get('modelo'),
                    "tipo": ant.get('tipo'),
                    "i_antena": i
                }
            })
        # Resumen por sector 
        resumen = resumen_antenas_sector(sector, lista_antenas)
        docs.append({
            "content": resumen,
            "metadata": {"section": "antenas_sector", "sector": sector, "tipo": "resumen"}
        })
    # Resumen global
    resumen_global = resumen_antenas_global(antenas_por_sector)
    docs.append({
        "content": resumen_global,
        "metadata": {"section": "antenas_sector", "tipo": "resumen_global"}
    })
        
    # 3. PRL
    prl = cap_json.get("prl", {})
    for tipo, subtipo_dict in prl.items():  # tipo = 'antenas', 'equipos'
        for subsection, items in subtipo_dict.items():  # subsection = 'ubicacion', 'acceso', 'seguridad'
            if items:
                if isinstance(items, list):
                    texto = (
                        f"{tipo.capitalize()}: {subsection} -> {', '.join(items)}."
                    )
                else:
                    texto = (
                        f"{tipo.capitalize()}: {subsection} -> {str(items)}."
                    )
                docs.append({
                    "content": texto,
                    "metadata": {
                        "section": "prl",
                        "tipo": tipo,
                        "subsection": subsection
                    }
                })
    # RESUMEN PRL
    texto_resumen_prl = resumen_prl(prl)
    if texto_resumen_prl:
        docs.append({
            "content": texto_resumen_prl,
            "metadata": {"section": "prl", "tipo": "resumen"}
        })

    # 4. TAREAS OPERADOR Y PROPIETARIO
    tareas = cap_json.get("tareas", {})
    for actor in ["operador", "propietario"]:
        bloque = tareas.get(actor, {})
        # 1. Doc largo con el texto completo (solo si existe)
        texto_completo = bloque.get("texto")
        if texto_completo:
            docs.append({
                "content": texto_completo,
                "metadata": {
                    "section": "tareas",
                    "actor": actor,
                    "tipo": "texto_completo" }})
        # 2. Docs atómicos por cada frase resumen y categoría
        resumen = bloque.get("resumen", {})
        for categoria, frases in resumen.items():
            for frase in frases:
                docs.append({
                    "content": frase.strip(),
                    "metadata": {
                        "section": "tareas",
                        "actor": actor,
                        "categoria": categoria }})
        # 3. Resumen narrativo global por actor
        resumen_global = resumen_narrativo_tareas(actor, resumen)
        if resumen_global:
            docs.append({
                "content": resumen_global,
                "metadata": {
                    "section": "tareas",
                    "actor": actor,
                    "tipo": "resumen_global" }})

    return docs

if __name__ == "__main__":
    nombre_archivo = "CAP_TFMA101_anon.json"
    id_cap = nombre_archivo.split("_")[1] # Extraer ID del nombre del archivo
    print(id_cap)
    # Cargar JSON
    cap_json = cargar_json("data/final/" + nombre_archivo)
    # Convertir a documentos
    docs = json_a_docs(cap_json)
    texts = [doc['content'] for doc in docs]
    # Generar embeddings con SentenceTransformer
    embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    embeddings = embedder.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")
    # Crear índice FAISS
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    # Guardar índice y documentos
    faiss.write_index(index, f"data/index/{id_cap}.faiss")
    with open(f"data/index/{id_cap}.pkl", "wb") as f:
        pickle.dump(docs, f)

    print(f"Indexados {len(docs)} documentos para el nodo {id_cap}")