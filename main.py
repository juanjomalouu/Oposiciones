# This is a sample Python script.
import json
import re
import fitz  # PyMuPDF para extraer texto del PDF
import requests
import folium
import os
from folium.plugins import Geocoder

# Press Mayús+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from folium.plugins import TagFilterButton


def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Paso 2: Identificar las ubicaciones con expresiones regulares (simplificado)
def parse_offers(text):
    # Dividimos el texto en secciones por ofertas basándonos en el patrón del ID de la oferta
    ofertas = re.split(r'\n(\d+)\n\((\d+)\)\s+', text)

    parsed_data = []

    for i in range(1, len(ofertas), 3):
        if i + 2 >= len(ofertas):
            break

        # Extracción de los campos
        oferta_id = ofertas[i].strip()
        codigo_centro = ofertas[i + 1].strip()
        detalles = ofertas[i + 2].strip()

        # Vacante: El primer número.
        vacante = oferta_id
        # Especialidad: El texto que sigue al código de la especialidad y se detiene en '- Vacante -'
        especialidad_match = re.search(r'\n\d+\s*-\s*(.+?)\s*-\s*Vacante\s*-', detalles, re.DOTALL)
        if especialidad_match:
            especialidad = especialidad_match.group(1).strip().replace('\n', ' ').replace("MAESTROS ", "")
        else:
            especialidad = "No tiene"

        # Centro: Lo que está después de '- Centro -' y antes de '- Cuerpo/Especialidad -'
        centro_match = re.search(r'^.*?\)', detalles, re.DOTALL)
        if centro_match:
            centro = centro_match.group(0).strip().replace('\n', ' ')
        else:
            centro = "No tiene"

        # Jornada: Lo que hay entre "Jornada" y "Duración"
        jornada_match = re.search(r'- Jornada -\s*(.*?)\s*- Duración -', detalles, re.DOTALL)
        if jornada_match:
            jornada = jornada_match.group(1).strip()
        else:
            jornada = "No tiene"

        # Duración: Lo que hay entre "Duración" y "Causa"
        duracion_match = re.search(r'- Duración -\s*(.*?)\s*- Causa -', detalles, re.DOTALL)
        if duracion_match:
            duracion = duracion_match.group(1).strip()
        else:
            duracion = "No tiene"

        # Causa: Lo que hay entre "Causa" y "Itinerante" o "Perfilada" si "Itinerante" no existe
        causa_match = re.search(r'- Cuerpo/Especialidad -\s*(.*?)\s*- Jornada -', detalles, re.DOTALL)
        if causa_match:
            causa = causa_match.group(1).strip()
        else:
            causa = "No tiene"

        # Itinerante: Lo que hay entre "Itinerante" y "Perfilada"
        itinerante_match = re.search(r'- Causa -\s*(.*?)\s*- Itinerante -', detalles, re.DOTALL)
        if itinerante_match:
            itinerante = itinerante_match.group(1).strip()
        else:
            itinerante = "No tiene"

        # Perfilada: Lo que hay entre "Perfilada" y "Perfiles" (si no está, es "No tiene")
        perfilada_match = re.search(r'- Perfilada -\s*(.*?)\s*- Perfiles -', detalles, re.DOTALL)
        if perfilada_match:
            perfilada = perfilada_match.group(1).strip()
        else:
            perfilada = "No tiene"

        # Perfiles: Lo que hay entre "Perfiles" y "Requisitos Vacante Perfilada" y NO contiene "Se requiere"
        perfiles_match = re.search(r'- Perfiles -\s*(.*?)(\s*- Requisitos Vacante Perfilada -|Se requiere)', detalles, re.DOTALL)
        if perfiles_match:
            perfiles = perfiles_match.group(1).strip()
        else:
            perfiles = "No tiene"

        # Requisitos Vacante Perfilada: Lo que hay entre "Requisitos Vacante Perfilada" y el final del texto o la siguiente sección
        requisitos_match = re.search(r'- Perfiles -\s*(.*?)\s*- Requisitos Vacante Perfilada -', detalles, re.DOTALL)
        if requisitos_match:
            requisitos_text = requisitos_match.group(1).strip()

            # Filtramos las líneas que contienen "Se requiere"
            lineas_con_requisitos = [linea.strip() for linea in requisitos_text.split('\n') if 'Se requiere' in linea]

            # Unimos las líneas relevantes en un solo texto
            if lineas_con_requisitos:
                requisitos = '\n'.join(lineas_con_requisitos).strip()
            else:
                requisitos = "No tiene"
        else:
            requisitos = "No tiene"

        # Guardar en un diccionario
        oferta_dict = {
            "Vacante": vacante,
            "Centro": centro,
            "Especialidad": especialidad,
            "Jornada": jornada,
            "Duración": duracion,
            "Causa": causa,
            "Itinerante": itinerante,
            "Perfilada": perfilada,
            "Perfiles": perfiles,
            "Requisitos": requisitos,
            "Coordenadas": get_lat_long(centro, api_key)
        }

        # Añadir a la lista de datos parseados
        parsed_data.append(oferta_dict)

    return parsed_data

# Paso 3: Buscar en Google Maps (necesitarás tu propia API Key)
def get_lat_long(location, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    if data['status'] == 'OK':
        location = data['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    return None

# Paso 4: Generar un mapa con Folium
def create_map(locations, mapName):
    # Crear un mapa centrado en la primera ubicación
    if locations:
        lat, lng = locations[0]['Coordenadas']
        my_map = folium.Map(location=[lat, lng], zoom_start=10)
    else:
        raise ValueError("No se encontraron ubicaciones para centrar el mapa.")

    # Estilos de marcadores para cada filtro
    marker_styles = {
        'Especialidad': {'color': 'blue', 'icon': 'glyphicon-education'},
        'Duración': {'color': 'green', 'icon': 'glyphicon-time'},
        'Causa': {'color': 'red', 'icon': 'glyphicon-warning-sign'},
        'Jornada': {'color': 'purple', 'icon': 'glyphicon-briefcase'}
    }
    i = 0
    Geocoder().add_to(my_map)
    # Añadir marcadores con diferentes estilos para cada tipo de filtro
    for loc in locations:
        print(i)
        i+=1
        lat_lng = loc['Coordenadas']
        if lat_lng:
            popup_content = f"""
               <strong>Vacante:</strong> {loc['Vacante']}<br>
               <strong>Centro:</strong> {loc['Centro']}<br>
               <strong>Especialidad:</strong> {loc['Especialidad']}<br>
               <strong>Jornada:</strong> {loc['Jornada']}<br>
               <strong>Duración:</strong> {loc['Duración']}<br>
               <strong>Causa:</strong> {loc['Causa']}<br>
               <strong>Itinerante:</strong> {loc['Itinerante']}<br>
               <strong>Perfilada:</strong> {loc['Perfilada']}<br>
               <strong>Perfiles:</strong> {loc['Perfiles']}<br>
               <strong>Coordenadas:</strong> {loc['Coordenadas']}<br>
               <strong>Requisitos:</strong> {loc['Requisitos']}
               """

            # Crear marcadores específicos para cada tipo de filtro
            tags = [loc[key] for key in marker_styles]
            folium.Marker(
                location=lat_lng,
                popup=folium.Popup(popup_content, max_width=12000),
                icon=folium.Icon(color='red', icon='glyphicon-map-marker'),
                tags=tags  # Todos los tags asociados con este marcador
            ).add_to(my_map)

    # Crear filtros dinámicos con TagFilterButton
    TagFilterButton(list(set([loc['Jornada'] for loc in locations])), clear_text="Limpiar filtros", button_style="primary", icon='glyphicon-time').add_to(my_map)
    TagFilterButton(list(set([loc['Especialidad'] for loc in locations])), clear_text="Limpiar filtros", button_style="primary", icon='glyphicon-user').add_to(my_map)
    TagFilterButton(list(set([loc['Duración'] for loc in locations])), clear_text="Limpiar filtros",button_style="primary", icon='glyphicon-calendar').add_to(my_map)
    TagFilterButton(list(set([loc['Causa'] for loc in locations])), clear_text="Limpiar filtros", button_style="primary", icon='glyphicon-user').add_to(my_map)

    # Guardar el mapa en un archivo HTML
    my_map.save(mapName)

def writeInformationInFile(locations, informationFilePath):
    with open(informationFilePath, 'w') as archivo:
        json.dump(locations, archivo)

def readFile(informationFilePath):
    locations = dict()
    with open(informationFilePath, 'r') as archivo:
        locations = json.load(archivo)
    return locations

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # Uso
    pdf_path = "VACANTES-22_07.pdf"
    #pdf_path = "VACANTES-22_07_removed.pdf"
    #pdf_path = "VACANTES-22_07_removed2.pdf"

    informationFilePath = pdf_path.replace(".pdf", ".json")
    mapName = pdf_path.replace(".pdf","_map.html")
    api_key = "AIzaSyAJWX2NT_ls9Xa4BiAtVuLmzfP8h_VqeXc"
    locations = dict()

    if os.path.exists(informationFilePath):
        print("Ya existe un archivo que leer")
        locations = readFile(informationFilePath)
        aaa
    else:
        print("No existe archivo, leyendo el pdf para parsearlo")
        text = extract_text_from_pdf(pdf_path)
        locations = parse_offers(text)
        writeInformationInFile(locations, informationFilePath)

    for resultado in locations:
        print(resultado)

    create_map(locations, mapName)
    print("Acabo")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
