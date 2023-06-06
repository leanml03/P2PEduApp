"""P2PEduApp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from P2PEduApp.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', welcome),
    path('welcome', welcome, name="welcome"),
    path('login', login, name="login"),
    path('home', home, name="home"),
    path('curso', curso, name="curso"),
    path('crear_curso',crear_curso,name="crear_curso"),
    path('registrar_curso',registrar_curso,name="registrar_curso"),
    path('cargar_archivo', cargar_archivo, name='cargar_archivo'),
    path('crear_eval',crear_eval, name='crear_eval'),
    path('calificar_eval',calificar_eval,name='calificar_eval'),
    path('cal_eval_notas',cal_eval_notas,name='cal_eval_notas'),
    path('evaluaciones',evaluaciones,name='evaluaciones'),
    path('gestor_archivos',gestor_archivos,name='gestor_archivos'),
    path('archivos_Cursos',archivos_Cursos,name='archivos_Cursos'),
    path('descargar_archivos',descargar_archivos,name='descargar_archivos'),
    path('subir_archivos',subir_archivos,name='subir_archivos'),
    path('foro', foro, name='foro'),
    path('crear_foro', crear_foro, name='crear_foro'),
    path('agregar_mensaje', agregar_mensaje, name='agregar_mensaje'),
    path('agregar_respuesta', agregar_respuesta, name='agregar_respuesta'),
    path('sincronizar', sincronizar, name='sincronizar'),
    path('error',error,name='error'),
    path('crear_votacion',crear_votacion,name='crear_votacion'),
    path('crear_votacion_mult',crear_votacion_mult,name='crear_votacion_mult'),
    path('votaciones',votaciones,name='votaciones'),
    path('crear_usuario',crear_usuario,name='crear_usuario'),
    path('descargar_usuario',descargar_usuario,name='descargar_usuario'),
    path('importar_usuario',importar_usuario,name='importar_usuario'),
    path('mostrar_resultados',mostrar_resultados,name='mostrar_resultados')


]
