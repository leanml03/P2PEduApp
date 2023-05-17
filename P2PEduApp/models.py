import os
import json
import shutil
from P2PEduApp.settings import BASE_DIR
import random


#Carga de los datos json
def cargar_datos_json():
    datos = {}
    ruta_datos = os.path.join(BASE_DIR, 'data')
    for archivo in os.listdir(ruta_datos):
        if archivo.endswith('.json'):
            with open(os.path.join(ruta_datos, archivo)) as f:
                datos[archivo[:-5]] = json.load(f)
    return datos


#Carga de los cursos
def load_courses():
    datos = {}
    ruta_datos = os.path.join(BASE_DIR, 'data/courses')
    for archivo in os.listdir(ruta_datos):
        if archivo.endswith('.json'):
            with open(os.path.join(ruta_datos, archivo)) as f:
                datos[archivo[:-5]] = json.load(f)
    return datos

#Carga del usuario
current_user=None
def load_profile():
    data=os.path.join(BASE_DIR,'data/user.json')
    try:
       f=open(data,"r")
    except:
        return
    datos= json.loads(f.read())
    print("Log: Usuario ha sido cargado")
    current_user=datos
    return datos                

def check_courses(name):
    print("entro")
    ruta_datos = os.path.join(BASE_DIR, 'data/courses')
    for archivo in os.listdir(ruta_datos):
        print(archivo[:-5])
        print(name)
        if archivo.endswith('.json'):
            if archivo[:-5]+".json" == name:
                    return True
    return False

def copy_export_file(path,path2):
    src = path #'/path/to/original/file.json'
    dst = path2 #'/path/to/new/location/file.json'
    shutil.copy(src, dst)

def get_random_image():
    img_dir = os.path.join(BASE_DIR, 'P2PEduApp/static/images')
    images = os.listdir(img_dir)
    img_name = random.choice(images)
    img_path = os.path.join(img_dir, img_name)
    return img_path, img_name


#Carga de los cursos
def reg_to_course(carne, token):
    ruta_datos = os.path.join(BASE_DIR, 'data/courses')
    for archivo in os.listdir(ruta_datos):
        if archivo.endswith('.json'):
            ruta_archivo = os.path.join(ruta_datos, archivo)
            with open(ruta_archivo, 'r+') as f:
                curso = json.load(f)
                if curso.get('token_curso') == token:
                    miembros = curso.get('miembros', [])
                    if carne not in miembros:
                        miembros.append(carne)
                        curso['miembros'] = miembros
                        f.seek(0)  # Mover el puntero de lectura/escritura al inicio del archivo
                        json.dump(curso, f, indent=4)  # Escribir el JSON modificado
                        f.truncate()  # Truncar el archivo para eliminar el contenido restante
                    break  # Terminar el bucle si se encuentra el archivo y se modifica

def load_forums(token_curso):
    ruta_cursos = os.path.join(BASE_DIR, 'data', 'courses')
    with open(ruta_cursos +'/{}.json'.format(token_curso), 'r') as f:
        data = json.load(f)
         
    foros = []
    for foro in data['foros']:
        foro_json = {
            'id': foro['id'],
            'autor': foro['autor'],
            'titulo': foro['titulo'],
            'mensajes': foro['mensajes']
        }
        foros.append(foro_json)
    return foros

def encontrar_foro_id(token):
    # Load course data from JSON file
    ruta_cursos = os.path.join(BASE_DIR, 'data', 'courses')
    with open(ruta_cursos +'/{}.json'.format(token), 'r') as f:
        data = json.load(f)

    if 'foros' in data and data['foros']:
        # If there are forums and they are not empty, find the last forum ID and add 1
        foro_ids = [foro['id'] for foro in data['foros']]
        new_id = max(foro_ids) + 1
    else:
        # If there are no forums, start ID count at 1
        new_id = 1

    return new_id


def obtener_ultimo_id_mensajes(mensajes):
    last_msg_id = 0

    for mensaje in mensajes:
        if mensaje['id'] > last_msg_id:
            last_msg_id = mensaje['id']

        if mensaje['respuestas']:
            last_resp_id = obtener_ultimo_id_mensajes(mensaje['respuestas'])
            if last_resp_id > last_msg_id:
                last_msg_id = last_resp_id

    return last_msg_id


def buscar_mensaje(mensajes, id_mensaje):
    for mensaje in mensajes:
        if mensaje['id'] == id_mensaje:
            return mensaje
        if mensaje['respuestas']:
            respuesta_encontrada = buscar_mensaje(mensaje['respuestas'], id_mensaje)
            if respuesta_encontrada:
                return respuesta_encontrada
    return None