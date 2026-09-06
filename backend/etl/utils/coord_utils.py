# modules/coord_utils.py
import re
import utm

def decimal_a_gms(valor, latitud=True):
    grados = int(abs(valor))
    minutos_float = (abs(valor) - grados) * 60
    minutos = int(minutos_float)
    segundos = round((minutos_float - minutos) * 60, 1)
    direccion = "N" if latitud and valor >= 0 else "S" if latitud else "E" if valor >= 0 else "W"
    return f"{grados}°{minutos}'{segundos}\"{direccion}"

def utm_a_gms(coord_dict):
    try:
        x = float(coord_dict["UTM_X"].replace(',', '.'))
        y = float(coord_dict["UTM_Y"].replace(',', '.'))
        huso_raw = coord_dict.get("UTM_HUSO", "31N").strip().upper()

        zone_number = int(re.match(r'\d{1,2}', huso_raw).group())
        zone_letter_match = re.search(r'[C-HJ-NP-X]', huso_raw)
        zone_letter = zone_letter_match.group() if zone_letter_match else 'N'

        lat_decimal, lon_decimal = utm.to_latlon(x, y, zone_number, zone_letter)
        lat_gms = decimal_a_gms(lat_decimal, True)
        lon_gms = decimal_a_gms(lon_decimal, False)

        return lat_gms, lon_gms

    except Exception as e:
        print("Error al convertir coordenadas UTM a GMS:", e)
        return None, None
