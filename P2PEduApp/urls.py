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
    path('welcome', welcome, name="welcome"),
    path('login', login, name="login"),
    path('home', home, name="home"),
    path('curso', curso, name="curso"),
    path('crear_curso',crear_curso,name="crear_curso"),
    path('registrar_curso',registrar_curso,name="registrar_curso"),
    path('cargar_archivo', cargar_archivo, name='cargar_archivo')
]
