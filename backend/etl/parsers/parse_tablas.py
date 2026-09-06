# parsers/parse_tablas.py
import pandas as pd
import re

def asignar_tecnologia_y_sector(df, col_origen='SECTOR T'):
    df = df.copy().reset_index(drop=True)
    df.rename(columns={col_origen: 'TECNOLOGIA'}, inplace=True)
    df['SECTOR'] = None

    sector = 0
    i = 0
    n = len(df)

    while i < n:
        cell = df.at[i, 'TECNOLOGIA']
        if pd.isna(cell):
            i += 1
            continue

        s = str(cell).replace('\n', ' ')
        techs = re.findall(r'.*?OSP', s)

        if not techs:
            i += 1
            continue

        sector += 1
        nombre_sector = f"SECTOR {sector}"

        for offset, tech in enumerate(techs):
            idx = i + offset
            if idx < n:
                df.at[idx, 'TECNOLOGIA'] = tech.strip()
                df.at[idx, 'SECTOR'] = nombre_sector

        i += len(techs)

        df['TECNOLOGIA'] = (
            df['TECNOLOGIA']
            .astype(str)
            .str.replace(r'^\s*SECTOR\s*\d+\s*', '', regex=True)
            .str.strip()
        )
    df.fillna(method='ffill', inplace=True)

    if 'MODELO' in df.columns:
        df['MODELO'] = (
            df['MODELO']
                .astype(str)
                .str.replace(r'\n', ' ', regex=True)
                .str.strip()
        )

    return df

def parsear_tabla_potencia(tablas):
    resultado = {}

    for tabla in tablas:
        if not tabla or not tabla[0]:
            continue

        cabecera = tabla[0][0].strip().upper()

        # Tipo 1: ITEM o TABLA POTENCIA CONSUMIDA (TYPICAL)
        if cabecera in ["ITEM", "TABLA POTENCIA CONSUMIDA (TYPICAL)"]:
            headers = tabla[1]  # Segunda fila como encabezado
            datos = tabla[2:]   # Resto de datos
            df = pd.DataFrame(datos, columns=headers)
            df.replace("--", 0, inplace=True)
            try:
                resultado = df.set_index("ITEM").to_dict(orient="index")
            except:
                pass

        # Tipo 2: TABLA DE CONSUMOS EQUIPOS DE RADIO
        elif "TABLA DE CONSUMOS" in cabecera:
            headers = tabla[1]
            datos = tabla[2:]
            df = pd.DataFrame(datos, columns=headers)
            try:
                resultado = df.set_index("ESTADO").to_dict(orient="index")
            except:
                pass

        # Tipo 3: CONSUMO EN DC DE EQUIPOS ORANGE EN E.F. DE PROPIEDAD
        elif "CONSUMO EN DC" in cabecera:
            headers = tabla[0]
            datos = tabla[1:]
            df = pd.DataFrame(datos, columns=headers)
            if df.shape[1] >= 2:
                df.columns = ['ESTADO', 'CONSUMO']
                resultado = df.set_index("ESTADO").to_dict(orient="index")

    return resultado

def parsear_hardware_texto(bloque):
    resultado = {
        "antenas": [],
        "rru": [],
        "bbu": None,
        "otros": []
    }

    modelos_antenas = re.findall(r"\b(\d+x)?\s?(ANTENAS?\s+[A-Z0-9\-]+)\b", bloque, flags=re.IGNORECASE)
    for cantidad, modelo in modelos_antenas:
        resultado["antenas"].append({
            "modelo": modelo.strip(),
            "cantidad": int(cantidad[:-1]) if cantidad and cantidad[:-1].isdigit() else 1
        })

    modelos_rru = re.findall(r"\b(\d+x)?\s?RRU['s]*\s*([A-Z0-9\-]+)([^\n]*)", bloque, flags=re.IGNORECASE)
    for cantidad, modelo, contexto in modelos_rru:
        tecnologias = re.findall(r"\b(LNR\d+|L\d+|NR\d+|GU\d+|IoT\d+)\b", contexto)
        resultado["rru"].append({
            "modelo": f"RRU {modelo.strip()}",
            "tecnologias": sorted(set(tecnologias))
        })

    modelos_bbu = re.findall(r"\b(BB\d{3,5})\b", bloque)
    if modelos_bbu:
        bbu_modelo = modelos_bbu[0]
        slots = re.findall(r"UBBP\w+|UMTP\w+|UPEU\w+", bloque)
        resultado["bbu"] = {
            "modelo": bbu_modelo,
            "slots": sorted(set(slots))
        }

    return resultado

def parsear_tabla_hardware(tablas):
    resultado = {
        "antenas": [],
        "rru": [],
        "bbu": None,
        "conectividad": [],
        "infraestructura": {}
    }
    for tabla in tablas:
        if not tabla or not tabla[0]:
            continue

        cabecera = tabla[0][0].strip().upper()

        if cabecera in ["TIPOHARDWARE", "TTIIPPOO HHAARRDDWWAARREE", "TIPO HARDWARE"]:
            headers = [
                h.upper().replace(" ", "").replace("TTIIPPOO", "TIPO")
                .replace("MMOODDEELLOO", "MODELO").replace("HHAARRDDWWAARREE", "HARDWARE")
                .replace("CCOONNEECCTTOORR", "CONECTOR")
                for h in tabla[0]
            ]
            datos = tabla[1:]
            df_hw = pd.DataFrame(datos, columns=headers)
            columnas_validas = [col for col in df_hw.columns if col in ['TIPOHARDWARE', 'MODELO', 'TIPOCONECTOR']]
            df_hw = df_hw[columnas_validas]
            df_hw = df_hw.dropna(how='all')
            df_hw.fillna("Desconocido", inplace=True)
            df_hw["TIPOHARDWARE"] = df_hw["TIPOHARDWARE"].str.strip().str.upper()
            df_hw["MODELO"] = df_hw["MODELO"].str.strip()
            df_hw["TIPOCONECTOR"] = df_hw["TIPOCONECTOR"].str.strip()
            for tipo, df in df_hw.groupby("TIPOHARDWARE"):
                resultado[tipo.lower()] = df.drop(columns="TIPOHARDWARE").to_dict(orient="records")

        elif "DATOS INFRAESTRUCTURAS BÁSICAS DEL SITE - ESTADO REFORMADO" in cabecera:
            datos = tabla[1:]
            resultado["infraestructura"]["basica"] = {
                fila[0]: fila[1] if len(fila) > 1 else None
                for fila in datos if fila and fila[0]
            }
            # También extraer texto para hardware_texto
            texto = " ".join(str(x) for fila in tabla for x in fila if x)
            resultado["hardware_texto"] = parsear_hardware_texto(texto)

        elif "DATOS INFRAESTRUCTURAS GENERALES DEL SITE - ESTADO REFORMADO" in cabecera:
            datos = tabla[1:]
            infra_gen = {
                fila[0]: fila[1] if len(fila) > 1 else None
                for fila in datos if fila and fila[0]
            }
            resultado["infraestructura"]["general"] = infra_gen

            # Extraer antenas
            if "3 Antenas" in infra_gen:
                modelos_ant = re.findall(r"\b(\d+x)?\s?ANTENAS?\s+([A-Z0-9\- ]+)\b", infra_gen["3 Antenas"], flags=re.IGNORECASE)
                for cantidad, modelo in modelos_ant:
                    resultado["antenas"].append({
                        "modelo": modelo.strip(),
                        "cantidad": int(cantidad[:-1]) if cantidad and cantidad[:-1].isdigit() else 1
                    })

            # Extraer RRU y BBU
            if "2 Equipos" in infra_gen:
                texto = infra_gen["2 Equipos"]
                modelos_rru = re.findall(r"\b(\d+x)?\s?RRU['s]*\s*([A-Z0-9\-]+)([^\n]*)", texto, flags=re.IGNORECASE)
                for cantidad, modelo, contexto in modelos_rru:
                    tecnologias = re.findall(r"\b(LNR\d+|L\d+|NR\d+|GU\d+|IoT\d+)\b", contexto)
                    resultado["rru"].append({
                        "modelo": f"RRU {modelo.strip()}",
                        "tecnologias": sorted(set(tecnologias))
                    })
                modelos_bbu = re.findall(r"\b(BB\d{3,5})\b", texto)
                if modelos_bbu:
                    bbu_modelo = modelos_bbu[0]
                    slots = re.findall(r"UBBP\w+|UMTP\w+|UPEU\w+", texto)
                    resultado["bbu"] = {
                        "modelo": bbu_modelo,
                        "slots": sorted(set(slots))
                    }

            # Extraer conectividad
            if "5 Coaxiales/Secciones" in infra_gen:
                resultado["conectividad"].append(infra_gen["5 Coaxiales/Secciones"])

    return resultado

def parsear_tabla_antenas(tablas):
    resultado = {}
    for tabla in tablas:
        if not tabla or not tabla[0]:
            continue
        cabecera = tabla[0][0].strip().upper()
        if cabecera in ["ANTENAS RF ORANGE", "AANNTTEENNAASS RRFF OORRAANNGGEE"]:
            datos = tabla[1:]
            df = pd.DataFrame(datos)
            df.iloc[:3] = df.iloc[:3].ffill(axis=0)
            nuevo_header = df.iloc[1].tolist()
            df = df.iloc[2:].reset_index(drop=True)
            df.columns = nuevo_header
            if 'ECNOLOGÍA' in df.columns:
                df.drop(columns='ECNOLOGÍA', inplace=True)
            seen = {}
            cols_únicos = []
            for col in df.columns:
                cnt = seen.get(col, 0) + 1
                seen[col] = cnt
                cols_únicos.append(col if cnt == 1 else f"{col}.{cnt-1}")
            df.columns = cols_únicos
            if 'SECTOR' in df.columns:
                df.fillna(method='ffill', inplace=True)
            elif 'SECTOR T' in df.columns:
                df = asignar_tecnologia_y_sector(df, col_origen='SECTOR T')
            for _, fila in df.iterrows():
                sector = fila.get("SECTOR", "SIN_SECTOR")
                if sector not in resultado:
                    resultado[sector] = []
                resultado[sector].append(fila.drop(labels=["SECTOR"]).to_dict())
        elif cabecera in ["ANTENAS OSP REFORMADO", "ANTENAS ORANGE"]:
            datos = tabla[1:]
            df = pd.DataFrame(datos)
            df.fillna(method='ffill', inplace=True)
            df.columns = df.iloc[1]
            df = df.iloc[2:].reset_index(drop=True)
            if cabecera == "ANTENAS OSP REFORMADO":
                df.columns = [
                    "SECTOR", "TECNOLOGIA", "TIPO_ANTENA", "ALTURA_TOP_ANT",
                    "ORIENTACION", "EDT", "MDT", "COAX_N", "COAX_TIPO",
                    "COAX_LONG", "FO_N", "FO_LONG", "VCC_N", "VCC_LONG"
                ]
            elif cabecera == "ANTENAS ORANGE":
                df.columns = [
                    "SECTOR", "TECNOLOGIA", "TIPO_ANTENA", "ORIENTACION", "ALTURA_BASE",
                    "EDT", "MDT", "COAX_NTIPO", "COAX_LONG", "FO_LONG", "VCC_LONG"
                ]
            for _, fila in df.iterrows():
                sector = fila.get("SECTOR", "SIN_SECTOR")
                if sector not in resultado:
                    resultado[sector] = []
                resultado[sector].append(fila.drop(labels=["SECTOR"]).to_dict())
    return resultado

def procesar_tabla_prl(table):
    # Buscamos el índice donde comienza "UBICACION DE EQUIPOS"
    idx_ue = next(
        (i for i, row in enumerate(table)
         if row and row[0] and "UBICACION DE EQUIPOS" in row[0].upper()),
        None
    )
    if idx_ue is None:
        raise ValueError("No encontré la sección 'UBICACION DE EQUIPOS'")

    # --- Bloque 1: ANTENAS Y PARABOLAS ---
    # Filas de datos reales, saltando título (0) y cabecera (1)
    datos1 = table[2: idx_ue]
    cols1 = [
        "UBICACION_VAL", "UBICACION_FLAG",
        "ACCESO ANTENAS_VAL", "ACCESO ANTENAS_FLAG",
        "SEGURIDAD_VAL",   "SEGURIDAD_FLAG"
    ]
    df1 = pd.DataFrame(datos1, columns=cols1)

    # Extraemos un único resumen:
    ubic = df1.loc[df1["UBICACION_FLAG"] == "X", "UBICACION_VAL"].tolist()
    acc  = df1.loc[df1["ACCESO ANTENAS_FLAG"] == "X", "ACCESO ANTENAS_VAL"].tolist()
    seg  = df1.loc[df1["SEGURIDAD_FLAG"] == "X", "SEGURIDAD_VAL"].tolist()

    prl_antenas = {
        "UBICACION": ubic,
        "ACCESO ANTENAS": acc,
        "SEGURIDAD": seg
    }
    # --- Bloque 2: UBICACION DE EQUIPOS ---
    # Filas de datos reales, saltando título (idx_ue) y cabecera (idx_ue+1)
    datos2 = table[idx_ue + 2 :]
    cols2 = [
        "UBICACION_VAL", "UBICACION_FLAG",
        "ACCESO BTS_VAL", "ACCESO BTS_FLAG",
        "SEGURIDAD_VAL",  "SEGURIDAD_FLAG"
    ]
    df2 = pd.DataFrame(datos2, columns=cols2)

    ubic2 = df2.loc[df2["UBICACION_FLAG"] == "X", "UBICACION_VAL"].tolist()
    acc2  = df2.loc[df2["ACCESO BTS_FLAG"] == "X", "ACCESO BTS_VAL"].tolist()
    seg2  = df2.loc[df2["SEGURIDAD_FLAG"] == "X", "SEGURIDAD_VAL"].tolist()

    prl_equipos = {
        "UBICACION": ubic2,
        "ACCESO BTS": acc2,
        "SEGURIDAD": seg2
    }

    return prl_antenas, prl_equipos