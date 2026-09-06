# cap_extractor.py
import fitz
import json
from backend.etl.ocr.ocr_text import extraer_texto_ocr_por_zona
from backend.etl.ocr.ocr_color import buscar_trabajos_por_color
from backend.etl.utils.pdf_utils import encontrar_pagina_por_titulo, extraer_tablas_de_pagina
from backend.etl.parsers.parse_coordenadas import parsear_coordenadas
from backend.etl.parsers.parse_identificadores import parsear_identificadores_emplazamiento
from backend.etl.parsers.parse_tablas import parsear_tabla_potencia, parsear_tabla_hardware, parsear_tabla_antenas, procesar_tabla_prl
from backend.etl.parsers.procesar_trabajos import procesar_trabajos_detallado

class CAPExtractor:
    def __init__(self, pdf_path, config):
        self.pdf_path = pdf_path
        self.config = config
        self.doc = fitz.open(pdf_path)
        self.resultado = {}
        self.tipo_cap = 'A' 

    def extraer_info_general(self):
        info = self._intentar_extraer_plantilla("A")
        if not info:
            info = self._intentar_extraer_plantilla("B")
        if info:
            self.resultado["emplazamiento"] = info["datos"]
            self.tipo_cap = info["tipo"]
        else:
            print("No se pudo identificar la plantilla del CAP.")

    def _intentar_extraer_plantilla(self, tipo):
        page = self.doc[0]
        rects = self.config["rectangles"]
        info_mejor = None
        tipo_mejor = None
        max_campos = 0
        for sufijo in ["1", "2"]:
            key_coords = f"coordenadas_{tipo}{sufijo}"
            if key_coords not in rects:
                continue
            texto_coords = extraer_texto_ocr_por_zona(page, tuple(rects[key_coords]))
            coords = parsear_coordenadas(texto_coords, False)
            print(coords)
            if not coords:
                continue
            nodo_txt = extraer_texto_ocr_por_zona(page, tuple(rects.get(f"nodo_{tipo}", [])))
            dir_txt = extraer_texto_ocr_por_zona(page, tuple(rects.get(f"direccion_{tipo}", [])))
            identificadores = parsear_identificadores_emplazamiento(nodo_txt + "\n" + dir_txt)
            total_campos = len(identificadores) + len(coords)
            if total_campos > max_campos:
                info_mejor = {**identificadores, **coords}
                tipo_mejor = f"{tipo}{sufijo}"
                max_campos = total_campos
        if info_mejor:
            print(f"Plantilla detectada: {tipo_mejor} ({max_campos} campos)","\n",info_mejor)
            return {"datos": info_mejor, "tipo": tipo_mejor}
        return None

    def extraer_calculos(self):
        rect = self.config["rectangles"].get(f"titulo_pagina_{self.tipo_cap[0]}", [])
        idx = encontrar_pagina_por_titulo(self.doc, tuple(rect), ["CALCULOS", "ACTUACIONES"])
        if idx is not None:
            tablas = extraer_tablas_de_pagina(self.pdf_path, idx)
            self.resultado['calculos'] = {"consumos": parsear_tabla_potencia(tablas),
                                          "hardware": parsear_tabla_hardware(tablas),
                                          "antenas": parsear_tabla_antenas(tablas)}
    
    def extraer_tabla_prl(self):
        titulos_prl = ["PLANTA P.R.L.","P.R.L. PLANTA","P.R.L. PLANTA GENERAL"]
        rect = self.config["rectangles"].get(f"titulo_pagina_{self.tipo_cap[0]}", [])
        idx = encontrar_pagina_por_titulo(self.doc, tuple(rect), titulos_prl)
        if idx is not None:
            tablas = extraer_tablas_de_pagina(self.pdf_path, idx)
            for tabla in tablas:
                if len(tabla) > 15:
                    prl_antenas, prl_equipos = procesar_tabla_prl(tabla)
                    self.resultado["prl"] = {"antenas": prl_antenas, "equipos": prl_equipos}

    def extraer_trabajos(self):
        trabajos = {}
        for empresa in self.config['colores_hsv'].keys():
            seccion = buscar_trabajos_por_color(self.pdf_path, empresa, self.config['colores_hsv'])
            if seccion:
                texto = seccion['texto']
                resumen = procesar_trabajos_detallado(texto)
                trabajos[empresa] = {"texto": texto,"resumen": resumen}
        self.resultado['tareas'] = trabajos

    def exportar_json(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.resultado, f, ensure_ascii=False, indent=4)

    def procesar(self):
        self.extraer_info_general()
        self.extraer_calculos()
        self.extraer_tabla_prl()
        self.extraer_trabajos()
