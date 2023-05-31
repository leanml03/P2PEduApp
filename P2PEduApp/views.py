import codecs
import os
import json
import hashlib
from django.contrib import messages
from django.shortcuts import render, redirect
#Importacion de los scripts de models (Manipulacion de los JSON)
from P2PEduApp.models import *

def welcome(request):

	user=load_profile()
	img_path, img_name = get_random_image()
	response = render(request, 'welcome.html', {'user':user,'image_path': img_path, 'image_name': img_name})
	response.set_cookie('selected_image', img_name)
	return response

def login(request):
	return render(request,'login.html')

def home(request):
	datos = load_courses()
	user=load_profile()
	selected_image = request.COOKIES.get('selected_image')
	nombre=request.POST.get('nombre')
	if request.method == 'POST':
		token = request.POST.get('token')
		mensaje='No se ha encontrado ningun curso con el Token introducido.'
		if(token==None):
			print("nope")
			mensaje='Se han sincronizado todos los cursos'
			
		for clave, valor in datos.items():
			if valor['token_curso'] == token:
				#miembros = valor['miembros']
				reg_to_course(user['carne'],token)
				print()
				mensaje="Se te ha agregado al curso "+valor["nombre_curso"] 
				break
		
		return render(request,'home.html',{'datos': datos,'user':user,'selected_image': selected_image, 'mensaje':mensaje})

	return render(request,'home.html',{'datos': datos,'user':user,'selected_image': selected_image})



def sincronizar(request):
	sincronizar_cursos()
	return render(request,'sincronizar.html')

def curso(request): #Pagina de Curso
	token=request.POST.get('token') #Se carga el token del curso que se le dio click con el button
	datos = load_courses() #se obtienen los datos de todos los cursos
	foros = load_forums(token)
	usuario=load_profile # se carga el perfil de usuario actual conectado
<<<<<<< Updated upstream


=======
	foros = load_forums(token)
	selected_image = request.COOKIES.get('selected_image')
>>>>>>> Stashed changes
	for clave, valor in datos.items(): # se recorren todos los cursos para obtener el que cumpla con la condicion de tener el mismo token que el que seleccionamos
		if(valor['token_curso'] == token):
			print(clave)
			print(valor)
			curso=valor
			break
<<<<<<< Updated upstream
	return render(request,'curso.html',{"curso":curso, "usuario":usuario, "token":token, 'foros':foros}) #se manda el curso que hemos seleccionado
=======
	return render(request,'curso.html',{"curso":curso, "usuario":usuario, "token":token,'selected_image': selected_image, 'foros':foros}) #se manda el curso que hemos seleccionado
>>>>>>> Stashed changes



def crear_curso(request): #crea el curso
	user=load_profile #Carga el perfil para darle autoria de la creacion del curso
	return render(request, 'crear_curso.html',{'user':user}) #Llama al html para crear el curso



def registrar_curso(request):
	if request.method == 'POST':
		nombre_curso = request.POST.get('nombre_curso')
		grupo_curso = request.POST.get('grupo_curso')
		carrera_curso = request.POST.get('carrera_curso')
		votan = request.POST.get('votan_curso')
		# Generar nombre cifrado para el archivo JSON
		token = hashlib.sha256((nombre_curso + grupo_curso + carrera_curso).encode('utf-8')).hexdigest()
		nombre_archivo = token + '.json'
		# Crear diccionario con los datos del curso
		datos_curso = {
			'nombre_curso': nombre_curso,
			'grupo_curso': grupo_curso,
			'carrera_curso': carrera_curso,
			'miembros': [],
			'foros': [],
			'token_curso': token,
			'votan': votan   
			
		}
		# Escribir el archivo JSON en la ubicación deseada
		ruta_cursos = os.path.join(BASE_DIR, 'data', 'courses')
		ruta_carpeta = os.path.join(ruta_cursos, token)
		ruta_archivo = os.path.join(ruta_cursos, nombre_archivo)

		os.makedirs(ruta_carpeta, exist_ok=True)  # crea la carpeta si no existe

		with open(ruta_archivo, 'w') as archivo:
			json.dump(datos_curso, archivo)
		reg_to_course(votan,token)
	return render(request, 'registrar_curso.html', {'token': token})

def cargar_archivo(request):
	if request.method == 'POST' and request.FILES['archivo']:
		archivo = request.FILES['archivo']
		# Aquí es donde guardarías el archivo en el directorio que quieras
		# Por ejemplo:
		ruta=os.path.join(BASE_DIR, 'data', 'courses')
		with open(ruta + archivo.name, 'wb+') as f:
			for chunk in archivo.chunks():
				f.write(chunk)
		return render(request, 'cargar_archivo.html')
	return render(request, 'cargar_archivo.html')

def crear_eval(request):
	token = request.GET.get('token')
	if request.method=='POST':
		nombre_eval=request.POST.get('nombre_eval')
		porcentaje=request.POST.get('range-value')
		fecha=request.POST.get('fecha')
		detalles=request.POST.get('detalles')
		archivo=request.POST.get('archivo')
		tokenCourse=request.POST.get('token')

		# Crear la carpeta de evaluaciones si no existe
		evaluaciones_dir = os.path.join(BASE_DIR, 'data', 'courses', tokenCourse,'evaluaciones')
		if not os.path.exists(evaluaciones_dir):
			os.makedirs(evaluaciones_dir)
		
			# Crear el archivo JSON y guardarlo en la carpeta de evaluaciones
		evaluacion = {
			'nombre': nombre_eval,
			'porcentaje': porcentaje,
			'fecha': fecha,
			'detalles': detalles,
			'calificaciones':{}
		}
		evaluacion_file = os.path.join(evaluaciones_dir, f'{nombre_eval}.json')
		with open(evaluacion_file, 'w') as f:
			json.dump(evaluacion, f)

		





		
		mensaje="La evaluacion se ha creado satisfactoriamente"
		return render(request, 'crear_eval.html',{'mensaje':mensaje,'token':tokenCourse})
	else:
		return render(request, 'crear_eval.html',{'token':token})

def calificar_eval(request):
	token = request.GET.get('token')
	# Obtener la lista de evaluaciones

	datos = load_courses() # Se obtienen los datos de todos los cursos
	usuario=load_profile # Se carga el perfil de usuario actual conectado

	for clave, valor in datos.items(): # Se recorren todos los cursos para obtener el que cumpla con la condicion de tener el mismo token que el que seleccionamos
		if valor['token_curso'] == token:
			curso=valor
			break

	evaluaciones_dir = os.path.join(BASE_DIR, 'data', 'courses', token, 'evaluaciones')
	evaluaciones = []
	for filename in os.listdir(evaluaciones_dir):
		if filename.endswith('.json'):
			with open(os.path.join(evaluaciones_dir, filename)) as f:
				evaluacion = json.load(f)
				evaluaciones.append(evaluacion)

	return render(request, 'calificar_eval.html', {"curso":curso, "token":token, "evaluaciones":evaluaciones})
def cal_eval_notas(request):
	if request.method == 'POST':
		if request.POST.get('estudiante'):
			token = request.POST.get('token')
			curso = request.POST.get('curso')
			estudiante = request.POST.get('estudiante')
			#evaluacion = json.loads(request.POST.get('evaluacion').replace("\'", "\""))
			nota = int(request.POST.get('nota'))
			evaluacion_name=request.POST.get('evaluacion')
			#Acceder al JSON de la evaluacion
			evaluaciones_dir = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones')
			for filename in os.listdir(evaluaciones_dir):
				if filename.endswith('.json') and filename.split('.')[0] == evaluacion_name:
					with open(os.path.join(evaluaciones_dir, filename)) as f:
						evaluacion = json.load(f)
						break
			if(nota>100 or nota<0):
				#Mensaje de rechazo a la peticion
				mensaje="La calificacion no se ha asignado debido a que los valores estan fuera de los rangos"
				#Reenvio de la evaluacion y el mensaje
				return render(request,'cal_eval_notas.html',{"evaluacion":evaluacion,"mensaje":mensaje,"token":token})
			else:
				# Actualizar la calificación del estudiante en el diccionario de calificaciones de la evaluación		
				evaluacion['calificaciones'][estudiante] = nota
				# Escribir el diccionario de evaluación actualizado en el archivo JSON correspondiente
				evaluacion_path = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones', evaluacion_name + '.json')
				with open(evaluacion_path, 'w') as f:
					json.dump(evaluacion, f)
			
				#Mensaje de exito
				mensaje="La calificacion del estudiante",estudiante,"se ha modificado correctamente."
				# Redirigir al usuario a la página de detalles de la evaluación
				return render(request,'cal_eval_notas.html',{"evaluacion":evaluacion,"mensaje":mensaje,"token":token})
		else:
			# Si la petición no es POST, redirigir al usuario a la página de inicio
			#carga del curso especifico y la evaluacion especifica
			token = request.POST.get('token')
			evaluacion_name=request.POST.get('evaluacion')
			print(token)
			evaluaciones_dir = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones')
			for filename in os.listdir(evaluaciones_dir):
				if filename.endswith('.json') and filename.split('.')[0] == evaluacion_name:
					with open(os.path.join(evaluaciones_dir, filename)) as f:
						evaluacion = json.load(f)
						break
					
			return render(request,'cal_eval_notas.html',{"evaluacion":evaluacion,"token":token})
def evaluaciones(request):
	#Se carga el usuario
	usuario=load_profile
	#Se carga el token del curso
	if not request.method=='POST': 
		token = request.GET.get('token')
	else:
		token=request.POST.get('token')
	
	#Se obtiene la direccion de la ubicacion de las evaluaciones
	evaluaciones_dir = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones')
	#Se verifica si hay evaluaciones en el curso
	if not os.path.exists(evaluaciones_dir):
		# si no se encuentra el folder de evaluaciones, se muestra un mensaje de error
		return render(request, 'curso.html', {'mensaje': 'El curso no tiene evaluaciones'})
	#Se cargan todas las evaluaciones y se almacenan en el arreglo
	evaluaciones = []
	#Se recorre los archivos para verificar las evaluaciones y agregarlas al arreglo
	for filename in os.listdir(evaluaciones_dir):
		if filename.endswith('.json'):
			with open(os.path.join(evaluaciones_dir, filename)) as f:
				evaluacion = json.load(f)
				evaluaciones.append(evaluacion)


	#Si el metodo es post se hace el registro del archivo subido
	if request.method == 'POST':
		try:
			archivo = request.FILES['archivo']
			archivoUploaded=True
		except:
			mensaje="No se ha seleccionado ningun archivo para subir a la evaluacion"
			archivoUploaded=False
		
		evaluacion_name = request.POST.get('evaluacion') 
		userCarne=request.POST.get('user')
		#Esta es la ubicacion de la carpeta de archivos de la evaluacion
		evaluacion_path = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones', evaluacion_name , 'files',userCarne)
		os.makedirs(evaluacion_path, exist_ok=True) #Verifica si la carpeta ya se encuentra
		if(archivoUploaded):
			with open(os.path.join(evaluacion_path, archivo.name), 'wb+') as destination:
				for chunk in archivo.chunks():
					destination.write(chunk)	
			#Ahora se abre el archivo JSON para modificar su interior
			for filename in os.listdir(evaluaciones_dir):
				if filename.endswith('.json') and filename==evaluacion_name+".json":
					with open(os.path.join(evaluaciones_dir, filename)) as f:
						eval = json.load(f)
			registro_entrega={userCarne:None}
			eval['calificaciones'].update(registro_entrega)
			
			evaluacion_dir = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones',evaluacion_name+'.json')
			with open(evaluacion_dir, 'w') as f:
				json.dump(eval, f)
			mensaje="Se ha subido el archivo a la evaluacion. "
		return render(request,'evaluaciones.html',{'evaluaciones':evaluaciones,'usuario':usuario,'token':token,'mensaje':mensaje})
	else:
		
		return render(request,'evaluaciones.html',{'evaluaciones':evaluaciones,'usuario':usuario,'token':token})
def gestor_archivos(request):
	token = request.GET.get('token')
	evaluacion_name = request.GET.get('evaluacion')
	
	path = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones',evaluacion_name,'files')  # aquí debes colocar la ruta a la carpeta que quieres mostrar
	 
	evaluaciones_dir = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'evaluaciones')
	return render(request,"gestor_archivos.html",{'token':token,'evaluacion':evaluacion})
import glob
def archivos_Cursos(request):
	token = request.GET.get('token')
	print(token)
	path = os.path.join(BASE_DIR, 'data', 'courses', str(token), 'files', '**', '*')

	filepaths = []
	for filepath in glob.glob(path, recursive=True):
		filepaths.append(filepath)

	return render(request, "archivos_Cursos.html", {'filepaths': filepaths,'token':token})

from django.http import HttpResponse,HttpResponseBadRequest
def descargar_archivos(request):
    if request.method == 'POST':
        archivos_seleccionados = request.POST.getlist('archivo')

        if not archivos_seleccionados:
            return HttpResponseBadRequest('No se seleccionó ningún archivo.')

        if len(archivos_seleccionados) > 1:
            return HttpResponseBadRequest('Solo se puede descargar un archivo a la vez.')

        archivo_seleccionado = archivos_seleccionados[0]
        nombre_archivo = os.path.basename(archivo_seleccionado)

        with open(archivo_seleccionado, 'rb') as archivo:
            response = HttpResponse(archivo.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
            return response

    return HttpResponseBadRequest('Método de solicitud no válido.')


<<<<<<< Updated upstream
=======
def error(request):
	return render(request,'error.html')


>>>>>>> Stashed changes
def foro(request):
    token = request.GET.get('token')
    id_foro = request.GET.get('id_foro')
    foros = load_forums(token)
    foro = foros[int(id_foro)-1]
    usuario = load_profile()
    
    return render(request,'foro.html',{"foro":foro, 'token':token, 'usuario':usuario}) #se manda el foro que hemos seleccionado

def crear_foro(request):
	usuario = load_profile()
	token = request.GET.get('token')
	if request.method == 'POST':
		token = request.POST.get('token')
		titulo_foro = request.POST.get('titulo_foro')
		creador_foro = request.POST.get('creador_foro')
		mensajes = []
		respuestas = []
		
		primer_mensaje = {
            "id": 1,
            "autor": creador_foro, # Assign the author's username to the 'autor' fiel
	        "mensaje": request.POST.get('comentario'),
            "respuestas": respuestas
        }
		mensajes.append(primer_mensaje)
		
		datos_foro = {
            "id": encontrar_foro_id(token),
            "autor": creador_foro, # Assign the author's username to the 'autor' field
            "titulo": titulo_foro,
            "mensajes": mensajes
        }

	
        # Escribir el archivo JSON en la lista de foros del curso
		ruta_cursos = os.path.join(BASE_DIR, 'data', 'courses')
		ruta_curso = os.path.join(ruta_cursos, token +'.json')
		
		with open(ruta_curso, 'r') as archivo_curso:
			datos_curso = json.load(archivo_curso)
			datos_curso['foros'].append(datos_foro)
		with open(ruta_curso, 'w') as archivo_curso:
			json.dump(datos_curso, archivo_curso, indent=4)
			mensaje="La evaluacion se ha creado satisfactoriamente"

		return render(request, 'crear_foro.html',{'mensaje':mensaje,'token':token, 'usuario':usuario})
	else:
		return render(request, 'crear_foro.html',{'token':token, 'usuario':usuario})
	
	
def agregar_mensaje(request):
	usuario = load_profile
	if request.method == 'POST':
		token_curso = request.POST.get('token')
		id_foro = int(request.POST.get('foro_id'))
		autor = request.POST.get('autor_mensaje')
		contenido = request.POST.get('texto')

		ruta_cursos = os.path.join(BASE_DIR, 'data', 'courses')
		ruta_curso = os.path.join(ruta_cursos, token_curso + '.json')
		with codecs.open(ruta_curso, 'r', encoding='utf-8') as f:
			data = json.load(f)


		foro = None
		for f in data['foros']:
			if int(f['id']) == id_foro:
				foro = f
				break
		if foro is None:
            # Foro no encontrado, manejar el error adecuadamente
			return HttpResponse('Foro no encontrado')

        # Obtener el último ID de todos los mensajes con todas sus respuestas correspondientes especificado por id_foro
		last_msg_id = obtener_ultimo_id_mensajes(foro['mensajes'])

        # Crear el nuevo mensaje
		nuevo_mensaje = {
            "id": last_msg_id + 1,
            "autor": autor,
            "mensaje": contenido,
            "respuestas": []
        }

        # Agregar el nuevo mensaje al foro
		foro['mensajes'].append(nuevo_mensaje)

        # Escribir el archivo JSON actualizado
		with codecs.open(ruta_curso, "w", encoding='utf-8') as f:
			json.dump(data, f, indent=2)
	
	return render(request,'foro.html',{"foro":foro, 'token':token_curso, 'usuario':usuario})


def agregar_respuesta(request):
	usuario = load_profile
	if request.method == 'POST':
		autor = request.POST.get('autor_mensaje')
		contenido = request.POST.get('texto')
		token_curso = request.POST.get('token')

		id_foro = int(request.POST.get('foro_id'))
		id_mensaje = int(request.POST.get('mensaje_id'))

		ruta_cursos = os.path.join(BASE_DIR, 'data', 'courses')
		ruta_curso = os.path.join(ruta_cursos, token_curso + '.json')

		with codecs.open(ruta_curso, 'r', encoding='utf-8') as f:
			data = json.load(f)
		foro = None



		for f in data['foros']:
			if f['id'] == id_foro:
				foro = f
				break


		if foro:
			last_resp_id = obtener_ultimo_id_mensajes(foro['mensajes'])
			nueva_respuesta = {
                "id": last_resp_id + 1,
                "autor": autor,
                "mensaje": contenido,
                "respuestas": []
            }
			mensaje = buscar_mensaje(foro['mensajes'], id_mensaje)

			if mensaje:
				mensaje['respuestas'].append(nueva_respuesta)
			else:
				raise ValueError(f"No se encontró ningún mensaje con el ID {id_mensaje}")

            # Escribir el archivo JSON actualizado
			with codecs.open(ruta_curso, "w", encoding='utf-8') as f:
				json.dump(data, f, indent=2)
		else:
			raise ValueError(f"No se encontró ningún foro con el ID {id_foro}")
	print('==========')	
	print('id_mensaje:',id_mensaje)
	print('==========')
<<<<<<< Updated upstream
	return render(request,'foro.html',{"foro":foro, 'token':token_curso, 'usuario':usuario})
=======
	return render(request,'foro.html',{"foro":foro, 'token':token_curso, 'usuario':usuario})

>>>>>>> Stashed changes
