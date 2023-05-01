import os
import json
import hashlib

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
	user=load_profile
	selected_image = request.COOKIES.get('selected_image')
	nombre=request.POST.get('nombre')
	return render(request,'home.html',{'datos': datos,'user':user,'selected_image': selected_image})



def curso(request): #Pagina de Curso
	token=request.POST.get('token') #Se carga el token del curso que se le dio click con el button
	datos = load_courses() #se obtienen los datos de todos los cursos
	usuario=load_profile # se carga el perfil de usuario actual conectado

	for clave, valor in datos.items(): # se recorren todos los cursos para obtener el que cumpla con la condicion de tener el mismo token que el que seleccionamos
		if(valor['token_curso'] == token):
			print(clave)
			print(valor)
			curso=valor
			break
	return render(request,'curso.html',{"curso":curso, "usuario":usuario}) #se manda el curso que hemos seleccionado



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