from comite import ComitéRecursos
from comite import ComitéRegistro
from persona import Persona
from recurso import Recurso
from conexión import Conexión

from collections import OrderedDict

import uuid
import logging
logging.basicConfig(level=logging.DEBUG)



class Comuna:
    """
    La comuna es un grupo de personas y recursos. Cada persona puede
    aportar recursos a la comuna y compartirlos.
    """

    CLIENT_NAME    = "Votán"
    CLIENT_ID      = "VT"
    CLIENT_VERSION = "0001"

    id_comuna                : str             # Identificador de esta comuna
    comité_recursos          : ComitéRecursos  # Comité para coordinar la traida de recursos
    comité_registro          : ComitéRegistro  # Comité para coordinar la traida de recursos

    persona                  : Persona
    personas_remotas         : [Persona]
    nombres_personas_remotas : dict
    tiempos_personas         : dict

    def __init__(self, puerto = 7896):
        """ 
        Genera el ID de la comuna (un texto de 20-bytes).
        """

        # Genera un ID tipo AZUREUS
        texto_aleatorio = str(uuid.uuid4()).split('-')[-1]
        self.id_comuna  = "-" + self.CLIENT_ID +\
                          self.CLIENT_VERSION + "-" + texto_aleatorio

        import random
        puerto_registro = puerto
	# Los dos puertos deberían ser distintos.
        puerto_recursos = puerto
        while puerto_recursos == puerto_registro:
        	puerto_recursos = random.randint(6000, 7000)

        self.persona = Persona()
        self.persona.comuna = True
        self.personas_remotas = []

        self.nombres_personas_remotas = {}
        self.tiempos_personas = {}

        # Se encarga de el manejo de recursos de la comuna
        self.comité_recursos = \
                ComitéRecursos(self.id_comuna, self.persona, \
                self.personas_remotas, self.nombres_personas_remotas, self.tiempos_personas, '127.0.0.1', puerto_recursos)

        # Se encarga de manejar el registro de personas en la comuna
        self.comité_registro = \
                ComitéRegistro(self.id_comuna, self.persona, \
                self.personas_remotas, self.nombres_personas_remotas, self.tiempos_personas, '127.0.0.1', puerto_registro,\
                self.comité_recursos.conexión.origen)

    def cerrar_comuna(self):
        """
        Finaliza todas las conexiones.
        """
        self.comité_recursos.cerrar_escucha()
        self.comité_registro.cerrar_escucha()

    def registrar_comuna(self, persona: Persona):
        """
        Registra una persona de tipo comuna en la lista de contactos
        (personas_remotas)
        """
        if persona.comuna == True:
            self.comité_registro.registrar_comuna(persona)

    def solicitar_personas(self):
        """
        Solicita las personas en la comuna
        """
        logging.debug(f'Solicitando a personas')
        self.comité_registro.solicitar_personas()

    def registrar_recurso_local(self, recurso: Recurso):
        """
        Registra un recurso en la comuna
        """
        self.comité_recursos.registrar_recurso(recurso)


    def gestionar_recurso_remoto(self, recurso: Recurso):
        """
        Gestiona entre todas las personas para traer el recurso
        """
        self.comité_recursos.gestionar_recurso(self.id_comuna, recurso)

    def listar_recursos_remotos(self):
        """
        Retorna los recursos remotos
        """
        return self.comité_recursos.listar_recursos_remotos()
        
    def listar_recursos_locales(self):
        """
        Retorna los recursos locales
        """
        return self.comité_recursos.listar_recursos_locales()
