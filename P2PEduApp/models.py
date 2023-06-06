import os
import json
import shutil
import time
import hashlib
import py7zr
from P2PEduApp.settings import BASE_DIR
import random
from btb_torrent import comuna

from btb_torrent.comuna import Comuna
from btb_torrent.persona import Persona
from btb_torrent.recurso import Recurso


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
def check_votan(carne,cursoid):
    datos = {}
    ruta_datos = os.path.join(BASE_DIR, 'data/courses')
    for archivo in os.listdir(ruta_datos):
        if archivo.endswith('.json'):
            with open(os.path.join(ruta_datos, archivo)) as f:
                curso = json.load(f)
                if curso.get('token_curso') == cursoid:
                    datos=curso
                    #print (datos)
    if datos['votan']==carne:
        return True
    else:
        return False
    
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

def sincronizar_cursos():
    comuna = Comuna(7777)       
    comuna_remota = Persona('127.0.0.1', 6666)      
    comuna_remota.comuna = True

    comuna.registrar_comuna(comuna_remota)
    comuna.solicitar_personas()
    
    time.sleep(3)

    for persona in comuna.comité_registro.personas_remotas:
        if persona.comuna == True:
            comuna.comité_registro.solicitar_recursos(persona)

    time.sleep(2)

    for persona_remota in comuna.comité_registro.personas_remotas:
        if persona_remota.comuna == True:
            for recurso in persona_remota.recursos:
                comuna.comité_registro.solicitar_detalle_recurso(persona_remota, recurso.info_hash)

    time.sleep(1)

    recursos = comuna.listar_recursos_locales()
    print(recursos)
    recursos = comuna.listar_recursos_remotos()
    print(recursos)

    recurso = Recurso()

    #hay que preguntar como se obtiene esta ruta en una pc diferente
    recurso.cargar_archivo_meta_info('courses.rar.vttorrent') 

    print('Traer este recurso', recurso.info_hash) 
    comuna.gestionar_recurso_remoto(recurso)

    print('#############')
    recursos = comuna.listar_recursos_locales()
    print(recursos)
    print('$$$$$$$$$$$$$')
    recursos = comuna.listar_recursos_remotos()
    print(recursos)

    extract_rar('courses.rar','data/')    





def compress_folder(folder_path, rar_path):
    # Crear un archivo RAR a partir de la carpeta
    with py7zr.SevenZipFile(rar_path, 'w') as archive:
        archive.writeall(folder_path, folder_path)

    print(f'Carpeta comprimida en archivo RAR: {rar_path}')


def extract_rar(rar_path, extract_path):
    # Extraer el contenido del archivo RAR
    with py7zr.SevenZipFile(rar_path, 'r') as archive:
        archive.extractall(extract_path)

    print(f'Archivo RAR descomprimido en: {extract_path}')

def iniciarlizar_comite_registro():
    cursos = Recurso('courses.rar')
    comuna = Comuna(6666)
    comuna.registrar_recurso_local(cursos)

def create_user(name,carne):
    user_folder = os.path.join(BASE_DIR, 'data')
    os.makedirs(user_folder, exist_ok=True)
    json_filename = f'user.json'
    uid = hashlib.sha256((name + carne).encode('utf-8')).hexdigest()
    json_filepath = os.path.join(user_folder, json_filename)
    user_data = {
            'carne': carne,
            'name': name,
            'uid': uid,
            
        }
    with open(json_filepath, 'w') as json_file:
        json.dump(user_data, json_file)

    # Imprimir un mensaje de éxito
    print(f"Usuario creado exitosamente en '{json_filepath}'")
def create_poll(poll_name,question,token):

    # Crear la ruta completa de la carpeta "poll"
    poll_folder = os.path.join(BASE_DIR, 'data','courses',token,'poll')
    os.makedirs(poll_folder, exist_ok=True) #Verifica si la carpeta ya se encuentra
    # Crear el nombre del archivo JSON utilizando el token y el nombre de la encuesta
    json_filename = f'{poll_name}.json'

    # Crear la ruta completa del archivo JSON dentro de la carpeta "poll"
    json_filepath = os.path.join(poll_folder, json_filename)

    # Crear el contenido del archivo JSON (aquí puedes definir la estructura de tu encuesta)
    poll_data = {
        'type': 'single',
        'token': token,
        'name': poll_name,
        'question': question,
        'yes':[],
        'no':[],
        'finished':False
        
    }

    # Guardar el contenido en el archivo JSON
    with open(json_filepath, 'w') as json_file:
        json.dump(poll_data, json_file)

    # Imprimir un mensaje de éxito
    print(f"Encuesta '{poll_name}' creada exitosamente en '{json_filepath}'")

def create_poll_mult(poll_name,question,token,opciones):

    # Crear la ruta completa de la carpeta "poll"
    poll_folder = os.path.join(BASE_DIR, 'data','courses',token,'poll')
    os.makedirs(poll_folder, exist_ok=True) #Verifica si la carpeta ya se encuentra
    # Crear el nombre del archivo JSON utilizando el token y el nombre de la encuesta
    json_filename = f'{poll_name}.json'

    # Crear la ruta completa del archivo JSON dentro de la carpeta "poll"
    json_filepath = os.path.join(poll_folder, json_filename)

    # Crear el contenido del archivo JSON (aquí puedes definir la estructura de tu encuesta)
    poll_data = {
        'type': 'multiple',
        'token': token,
        'name': poll_name,
        'question': question,
        'opciones':opciones,
        'lista_respuestas':[[],[],[],[],[]],
        'voted':[],
        'finished':False
        
    }

    # Guardar el contenido en el archivo JSON
    with open(json_filepath, 'w') as json_file:
        json.dump(poll_data, json_file)

    # Imprimir un mensaje de éxito
    print(f"Encuesta '{poll_name}' creada exitosamente en '{json_filepath}'")

def return_polls(token):
    # Obtener la ruta base de tu proyecto Django
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Crear la ruta completa de la carpeta "poll"
    poll_folder = os.path.join(base_dir,'data','courses',token, 'poll')

    # Verificar si la carpeta "poll" existe
    if os.path.exists(poll_folder):
        # Obtener la lista de archivos en la carpeta "poll"
        poll_files = os.listdir(poll_folder)

        # Filtrar los archivos por aquellos que coincidan con el token específico
        matching_polls = [file for file in poll_files if file.startswith(token)]

        # Crear una lista para almacenar los datos de las encuestas encontradas
        polls_data = []

        # Iterar sobre los archivos de encuesta encontrados
        for poll_file in matching_polls:
            # Crear la ruta completa del archivo JSON
            poll_filepath = os.path.join(poll_folder, poll_file)

            # Leer el contenido del archivo JSON
            with open(poll_filepath, 'r') as json_file:
                poll_data = json.load(json_file)

            # Agregar los datos de la encuesta a la lista
            polls_data.append(poll_data)

        # Retornar la lista de encuestas encontradas
        return polls_data

    else:
        # Si la carpeta "poll" no existe, retornar una lista vacía
        return []
    
def get_json_files(folder_path):
    json_files = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.json'):
            file_path = os.path.join(folder_path, file_name)
            with open(file_path) as json_file:
                json_data = json.load(json_file)
                json_files.append(json_data)
    return json_files   

def votar(votacion_name,votacion_token,votacion_type,respuesta,usuario):
    print(usuario)
    
    file_path=os.path.join(BASE_DIR, 'data','courses',votacion_token,'poll',votacion_name+".json")
    with open(file_path, 'r') as json_file:
        poll_data = json.load(json_file)

    if votacion_type == 'single':
        
        print(respuesta)
        if respuesta == "YES":
            poll_data['yes'].append(usuario['carne'])
        else:
            poll_data['no'].append(usuario['carne'])
        with open(file_path, 'w') as json_file:
            json.dump(poll_data, json_file)
        # El usuario seleccionó la opción YES
        # Realiza la lógica correspondiente aquí
       
        # El usuario seleccionó la opción NO
        # Realiza la lógica correspondiente aquí
    else:
        indice=poll_data['opciones'].index(respuesta)
        poll_data['lista_respuestas'][indice].append(usuario['carne'])
        poll_data['voted'].append(usuario['carne'])

        with open(file_path, 'w') as json_file:
            json.dump(poll_data, json_file)

        """
        i=0
        for options in poll_data['lista_respuestas']:
            if(respuesta in poll_data['opciones']):
                poll_data['lista_respuestas'][i].append(usuario['carne'])
                break
            i+=1 
        poll_data['voted'].append(usuario['carne'])

    with open(file_path, 'w') as json_file:
        json.dump(poll_data, json_file)
    """
    # Imprimir un mensaje de éxito
    print(f"Voto registrado exitosamente en '{file_path}'")
