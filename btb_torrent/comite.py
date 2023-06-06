from bitstring import BitArray
from hashlib import sha1
from collections import OrderedDict
from socket import inet_aton, inet_ntoa

from btb_torrent.persona     import Persona
from btb_torrent.conexión    import Conexión
from btb_torrent.recurso     import Recurso

import os
import copy
import struct
import threading
import binascii
import bencodepy
import time

import logging
logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.ERROR)



class ComitéRecursos():
    """
    Implementa el protocolo de comunicación entre varias personas
    involucradas en la comuna para transferir archivos

    Una comuna es un conjunto de personas que comparten recursos.
    
    Nota: El protocolo solo va a formar y desarmar los mensajes.
        - Si envía un mensaje (métodos env_), retorna un bytes codificado utf-8
        - Si recibe un mensaje (métodos rec_), retorna un diccionario ordenado 
    """
    # Determina cuantas veces puede reenviar cada pieza
    MAX_REENVIOS      = 2 # Poner como -1 para infinitos

    # Determina cuantas veces puede volver a buscar remotos
    MAX_RESALUDAR     = 2 # Poner como -1 para infinitos

    # Determina cuantos segundos puede esperar para que alguien responda
    MAX_ESPERAR       = 2 # Poner como -1 para infinitos
    
    # Determina si se debería borrar un recurso que no se completó
    BORRAR_INCOMPLETO = True

    MAX_VIDA          = 10 # cantidad de segundos de mantener viva una conexión

    cerrando          = False # Un parametro para indicar al sistema que se está parando el funcionamiento


    id_columna               : str

    # Yo que tengo la conexión (el que coordina la recepción de piezas)
    conexión                 : Conexión
    persona_local            : Persona

    # Estos son los datos a usar ahora.
    recursos                 : dict   # Recurso  que se está solicitando
    personas_remotas         : list      # Lista de personas que me contestaron el saludo
    nombres_personas_remotas : dict
    tiempos_personas         : dict # Guarda la útilma vez que ocurrió una conexión válida con la persona
    escucha                  : threading.Thread

    recursos_parciales       : dict # Los involucrados en mandar un recurso

    # Constructor
    def __init__(self, id_comuna, persona, personas_remotas, nombres_personas_remotas, tiempos_personas,  ip,  puerto):

        # Coloca el id de comuna
        self.id_comuna = id_comuna

        # Inicializa el puerto de escucha
        self.persona_local = persona

        self.conexión = Conexión((ip, puerto))

        # personas remotas que son contacto
        self.personas_remotas = personas_remotas

        # Para poder identificar las personas
        self.nombres_personas_remotas = nombres_personas_remotas

        self.tiempos_personas = tiempos_personas

        #       Fuente
        # pares (ip, puerto) => Recurso Para recursos que se trae
        self.recursos_parciales = {}
        
        #       Destino
        # pares (ip, puerto) => Recurso
        self.recursos_enviando = {}

        self.escucha = threading.Thread(target=self.iniciar_escucha)
        self.escucha.start()

    def iniciar_escucha(self):
        """
        Inicializa la escucha permanente para este protocolo
        """
        while True:
            # Este try captura los errores de recepción
            try:
                # Este try captura cuando el socket se cierra
                try:
                    # Recibimos el mensaje
                    mensaje_recibido, persona = self.conexión.recibir_mensaje()
                except OSError as ex:
                    if self.cerrando:
                        break
                    logging.exception(f'Ocurrió una excepción OSError en la recepción de información')
                    raise ex

                # Procesamos el mensaje
                mensaje_respuesta = self.procesar_mensaje(mensaje_recibido, persona)
  
                # Reenvía el mensaje de respuesta
                if mensaje_respuesta != None:
                    self.conexión.enviar_mensaje(persona, mensaje_respuesta)

            except ErrorRecepción as ex:
                logging.exception('Ocurrió un error cuando se recibió un mensaje')

                if ex.crítico:
                    logging.critical('El error de recepción es crítico!')
                    raise ex

    def cerrar_escucha(self):
        """
        Para el programa
        """
        logging.debug('Cerrando comité de recursos')

        self.cerrando = True
        self.conexión.cerrar_conexión()
        self.escucha.join()

    def registrar_recurso(self, recurso: Recurso):
        """
        Registra un recurso en la persona local
        """

        self.persona_local.recursos.append(recurso)

    def listar_recursos_remotos(self):
        """
        Lista todos los elementos propios de las personas remotas
        """
        lista_recursos = []

        for persona_remota in self.personas_remotas:
            for recurso in persona_remota.recursos:
                lista_recursos.append((str(persona_remota), recurso.info_hash))

        return lista_recursos

    def listar_recursos_locales(self):
        """
        Lista todos los recursos propios
        """
        lista_recursos = []

        for recurso in self.persona_local.recursos:
            lista_recursos.append(recurso.info_hash)

        return lista_recursos


    def gestionar_recurso(self, id_comuna: str, recurso: Recurso):
        """
        Recibe un recurso
        """
        logging.debug(f'Inicio solicitud del recurso {self.personas_remotas}')

        # Preparamos los mensajes
        mensaje_saludo = self.env_saludo(id_comuna, recurso.info_hash)
        mensaje_interesado = self.env_interesado()

        # Los contraladores de ciclos para evitar ciclos infinitos
        ciclo_saludo = 0
        continuar = True

        self.persona_local.recursos.append(recurso)
        
        cantidad_piezas = recurso.atributos['info']['length']
        recurso.piezas = BitArray('0b' + '0'*cantidad_piezas)

        # Por lo tanto que no hemos "sobresaludado"
        while ciclo_saludo != self.MAX_RESALUDAR:

            ciclo_saludo += 1
            logging.debug(f'Ciclo de saludo actual: {ciclo_saludo}/{self.MAX_RESALUDAR}')

            # Aca saludo a todo el mundo y luego voy bretiando con lo que va llegando
            for persona_remota in self.personas_remotas:
                if not persona_remota.comuna:
                    self.conexión.enviar_mensaje(persona_remota, mensaje_saludo)

                    if str(persona_remota) not in self.recursos_parciales or self.recursos_parciales[str(persona_remota)][0] != recurso:
                        self.recursos_parciales[str(persona_remota)] = [recurso, BitArray()]

                    self.nombres_personas_remotas[str(persona_remota)] = persona_remota
                    self.tiempos_personas[str(persona_remota)] = time.time() + self.MAX_ESPERAR

            # Enviamos mensaje de "estoy interesado", porque así lo pide el protocolo
            for persona_remota in self.personas_remotas:
                if not persona_remota.comuna and persona_remota.esta_bloqueando:
                    self.conexión.enviar_mensaje(persona_remota, mensaje_interesado)
                    persona_remota.estoy_interesado = True
            
            bloqueados = 1

            # Espera para que alguien nos desbloquee por nuestro mensaje de "estoy interesado"
            while self.MAX_ESPERAR >= bloqueados > 0:
                time.sleep(1)
                bloqueados += 1

                for nombre_persona_remota in list(self.recursos_parciales.keys()):
                    persona_remota = self.nombres_personas_remotas[str(nombre_persona_remota)]
                    if persona_remota.estoy_interesado and not persona_remota.esta_bloqueando:
                        bloqueados = 0
                        break

            # Si pasó el límite de tiempo, volvamos al inicio del ciclo
            if bloqueados > 0:
                continue

            indice_pieza = 0
            repeticiones = 0

            # Acá es donde me vuelvo loco con el algoritmo de solicitud de piezas
            continuar = True 

            while continuar and repeticiones != self.MAX_REENVIOS:
                continuar = False

                fallos = 0

                # A cada persona remota le solicia una pieza distinta
                for nombre_persona_remota in list(self.recursos_parciales.keys()):
                    persona_remota = self.nombres_personas_remotas[nombre_persona_remota]
                    if persona_remota.estoy_interesado and not persona_remota.esta_bloqueando and not self.__expirar_tiempo(persona_remota) and self.recursos_parciales[nombre_persona_remota][1][indice_pieza] == 1:

                        # Encuentra la siguiente pieza que me hace falta
                        while recurso.piezas[indice_pieza] != 0 and indice_pieza < cantidad_piezas - 1:
                            indice_pieza += 1

                        # Hace la solicitud de la pieza
                        mensaje = self.env_solicitar(indice_pieza, 0, 16384)  # 16K
                        self.conexión.enviar_mensaje(persona_remota, mensaje)

                        # Pasa a la siguiente pieza
                        indice_pieza = (indice_pieza + 1)%cantidad_piezas
                        if indice_pieza == 0:
                            repeticiones += 1
                    else:
                        fallos += 1

                # Si por alguna razón nadie está dispuesto o capaz de comunicar con nosotros, subimos el contador de la pieza para no quedarnos pegados
                if fallos >= len(self.recursos_parciales.keys()):
                    indice_pieza = (indice_pieza + 1)%cantidad_piezas
                    if indice_pieza == 0:
                        repeticiones += 1

                time.sleep(0.1)
                logging.debug(f'{recurso.piezas}, {self.recursos_parciales}, {self.personas_remotas}')

                # Determina si ya tengo todas las piezas
                if recurso.piezas_recibidas < cantidad_piezas:
                    continuar = True

            if not continuar:
                break

        if continuar:
            logging.error('No se logró recibir el recurso completo...')

            # Si no logramos completar el recurso con los intentos permitidos, lo destruimos
            # Sin embargo, su información queda en el sistema si self.BORRAR_INCOMPLETO == False
            if self.BORRAR_INCOMPLETO:
                if recurso.ruta_en_disco != None:
                    os.remove(recurso.ruta_en_disco)

            if recurso.piezas == None or recurso.piezas_recibidas == 0 or self.BORRAR_INCOMPLETO:
                self.persona_local.recursos.remove(recurso)

        # Finalmente decimos a todas las personas que ya no estamos interesados
        for nombre_persona_remota in list(self.recursos_parciales.keys()):
            persona_remota = self.nombres_personas_remotas[nombre_persona_remota]
            mensaje = self.env_sin_interes()
            self.conexión.enviar_mensaje(persona_remota, mensaje)
            persona_remota.estoy_interesado = False

        # Borramos el recurso de la lista de recursos parciales
        self.recursos_parciales = {k:v for k, v in self.recursos_parciales.items() if v[0] != recurso}

    # Wire protocol
    def procesar_mensaje(self, data, persona):
        """
        Determina el tipo de mensaje para procesarlo con la función
        adecuada
        """
        # Si la persona no nos saludo desde antes, la ignoramos
        if len(data) != 68:
            if str(persona) not in self.nombres_personas_remotas:
                self.__resolver_desconocido(persona, KeyError(f'No se conoce a {persona}'))

            if self.__expirar_tiempo(persona): # Por si se expiró la conexión

                self.__resolver_tiempo(persona, ValueError(f'La conexión con {persona} ya se expiró'))

            persona = self.nombres_personas_remotas[str(persona)]

            self.tiempos_personas[str(persona)] = time.time() # Mantiene viva la "conexión"

        if len(data) == 68: # Saludo
            logging.debug(f'Nos saluda {persona}')

            # Alguien me mandó un saludo
            try:
                mensaje = self.rec_saludo(data)
            except Exception as ex:
                self.__resolver_saludo(persona, ex)

            # Si las versiones son diferentes
            if self.id_comuna[1:7] != mensaje['id_persona'][1:7]:
                self.__resolver_saludo(persona, TypeError(f"El cliente de {persona} es {mensaje_recibido['id_persona'][1:7]}. Esta versión no es compatible con el cliente actual {self.id_comuna[1:7]}"))

            # Busco el identificador de recurso entre los recursos de la persona_local
            id_recurso = mensaje['info_hash']
            recurso_solicitado = None

            # Busco si tengo el recurso
            for recurso in self.persona_local.recursos:
                if id_recurso == recurso.info_hash:
                    recurso_solicitado = recurso
                    break

            # Si el recurso no está detengo la conexión
            if recurso_solicitado == None:
                return

            # Registramos a la persona
            if str(persona) not in self.nombres_personas_remotas:
                self.personas_remotas.append(persona)
                self.nombres_personas_remotas[str(persona)] = persona
            else:
                self.__expirar_tiempo(persona)

            self.tiempos_personas[str(persona)] = time.time()
            self.recursos_enviando[str(persona)] = (persona, recurso_solicitado)
            nuevo_mensaje = self.env_listar(recurso_solicitado)

            return nuevo_mensaje

        elif len(data) == 4: # Mantener viva
            try:
                mensaje = self.rec_mantener_viva(data)
            except Exception as ex:
                self.__resolver_mantener_viva(persona, ex)

        elif data[4] == 0: # Bloquear

            logging.debug(f'0 Bloqueados por {persona}')

            try:
                mensaje = self.rec_bloquear(data)
            except Exception as ex:
                self.__resolver_bloquear(persona, ex)

            # Si nos bloquea, lo olvidamos
            if str(persona) in self.recursos_parciales:
                self.recursos_parciales.pop(str(persona))

            persona.esta_bloqueando = True

        elif data[4] == 1: # Desbloquear

            logging.debug(f'1 Desbloqueados por {persona}')

            try:
                mensaje = self.rec_desbloquear(data)
            except Exception as ex:
                self.__resolver_desbloquear(persona, ex)

            persona.esta_bloqueando = False

        elif data[4] == 2: # Interesado

            logging.debug(f'2 {persona} está interesado')

            try:
                mensaje_recibido = self.rec_interesado(data)
            except Exception as ex:
                self.__resolver_sin_interesado(persona, ex)

            # Por de facto desbloqueamos a la persona si está interesada
            if not persona.esta_interesado:
                persona.esta_interesado = True
                mensaje = self.env_desbloquear()
                persona.estoy_bloqueando = False

                return mensaje

        elif data[4] == 3: # Sin interés

            logging.debug(f'3 {persona} no está interesado')

            try:
                mensaje_recibido = self.rec_sin_interes(data)
            except Exception as ex:
                self.__resolver_sin_interes(persona, ex)

            # Borramos su información si ya no nos quiere
            if str(persona) in self.recursos_enviando:
                self.recursos_enviando.pop(str(persona))

            if persona.esta_interesado:
                persona.esta_interesado = False
                mensaje = self.env_bloquear()
                persona.estoy_bloqueando = True

                return mensaje

        elif data[4] == 4: # Existe

            logging.debug('4 existe')

            if persona not in self.recursos_parciales:
                self.__resolver_existe(persona, ValueError(f'{persona} no debería mandar este tipo de mensaje'))

            try:
                mensaje = self.rec_existe(data)
            except Exception as ex:
                self.__resolver_existe(persona, ex)

            if mensaje['índice_pieza'] >= len(self.recursos_parciales[persona][1]):
                self.__resolver_existe(persona, IndexError(f"Índice de la pieza fuera de rango: {mensaje['índice_pieza']}"))

            self.recursos_parciales[persona][1][mensaje['índice_pieza']] = 1

        elif data[4] == 5: # Recibo el listar
            logging.debug('5 listar')

            if str(persona) not in self.recursos_parciales:
                self.__resolver_listar(persona, ValueError(f'{persona} no debería mandar este tipo de mensaje'))

            # Recibo la lista de piezas
            try:
                mensaje = self.rec_listar(data)
            except Exception as ex:
                self.__resolver_listar(persona, ex)

            logging.debug(mensaje['listado'])

            # Si el listado tiene longitud incorrecta
            if len(mensaje['listado']) - 8 > self.recursos_parciales[str(persona)][0].atributos['info']['length'] or len(mensaje['listado']) < self.recursos_parciales[str(persona)][0].atributos['info']['length']:
                self.recursos_parciales.pop(str(persona))

                self.__resolver_listar(persona, IndexError(f"El listado tiene tamaño incorrecto: {len(mensaje['listado'])}"))

            # Recuerdo la lista de piezas
            self.recursos_parciales[str(persona)][1] = mensaje['listado']

        elif data[4] == 6: # Solicitar

            # Si el mae no nos saludo para el archivo, entonces qué hace hablando con nosotros.
            if not persona.esta_interesado or persona.estoy_bloqueando or not str(persona) in self.recursos_enviando:
                self.__resolver_solicitar_pieza(persona, ValueError(f'{persona} no debería mandar este tipo de mensaje'))

            # Recibí una solicitud de una pieza
            try:
                mensaje_recibido = self.rec_solicitar(data)
            except Exception as ex:
                self.recursos_enviando.pop(str(persona))
                self.__resolver_solicitar_pieza(persona, ex)

            índice_pieza = mensaje_recibido['índice_pieza']
            byte_inicial = mensaje_recibido['byte_inicial']
            cantidad_bytes = mensaje_recibido['cantidad_bytes']

            logging.debug(f'6 enviar pieza {índice_pieza} {persona}')

            # Acá saco la pieza del recurso que estoy compartiendo
            bloque = None

            _, recurso = self.recursos_enviando[str(persona)]

            if recurso.piezas != None:
                if índice_pieza >= len(recurso.piezas) or recurso.piezas[índice_pieza] == 0:
                    self.recursos_enviando.pop(str(persona))
                    self.__resolver_solicitar_pieza(persona, IndexError(f'No se posee a la pieza {índice_pieza}'))

            # acá agarro el archivo y leer la seccion solicitada y
            # tirarle sólido al comité que me lo está solicitando.
            try:
                with open(recurso.ruta_en_disco, 'rb') as archivo:
                    archivo.seek(índice_pieza*16384+byte_inicial, os.SEEK_SET)
                    bloque = archivo.read(cantidad_bytes)

            except Exception as ex:
                self.recursos_enviando.pop(str(persona))
                self.__resolver_solicitar_pieza(persona, ex)

            # Envía la pieza
            mensaje = self.env_pieza(índice_pieza, byte_inicial, bloque) #16K

            return mensaje

        elif data[4] == 7: # Pieza

            if not persona.estoy_interesado or persona.esta_bloqueando or str(persona) not in self.recursos_parciales:
                self.__resolver_recibir_pieza(persona, ValueError(f'{persona} no debería mandar este tipo de mensaje'))

            # Recibo la pieza que me enviaron
            try:
                mensaje_recibido = self.rec_pieza(data)
            except Exception as ex:
                self.recursos_parciales.pop(str(persona))
                self.__resolver_recibir_pieza(persona, ex)

            índice_pieza = mensaje_recibido['índice_pieza']
            byte_inicial = mensaje_recibido['byte_inicial']
            bloque       = mensaje_recibido['bloque']

            logging.debug(f'7 recibir pieza {índice_pieza} {persona}')

            # Actualiza la lista de piezas con la pieza recibida
            recurso, _ = self.recursos_parciales[str(persona)]

            # Comparamos el sha1
            if recurso.atributos['info']['pieces'][40*índice_pieza:40*índice_pieza+40] != sha1(bloque).hexdigest():
                self.recursos_parciales.pop(str(persona))
                self.__resolver_recibir_pieza(persona, ValueError(f'El sha1 recibido para la pieza {índice_pieza} no coincide'))

            # No ocupo una pieza que ya tengo...
            if recurso.piezas[índice_pieza] == 1:
                return

            if recurso.ruta_en_disco == None:
                recurso.ruta_en_disco = recurso.nombre
                open(recurso.ruta_en_disco, 'a').close()

            # Escribo en el archivo el segmento que me enviaron
            try:
                with open(recurso.ruta_en_disco, 'r+b') as archivo:
                    archivo.seek(índice_pieza*16384+byte_inicial, os.SEEK_SET)
                    archivo.write(bloque)

            except Exception as ex:
                self.recursos_parciales.pop(str(persona))
                self.__resolver_recibir_pieza(persona, ex)

            recurso.piezas[índice_pieza] = 1
            recurso.piezas_recibidas += 1

        elif data[4] == 8: # Cancel

            # Rebibo un mensaje de cancelar el mandar de la pieza que pidieron

	    # FYI: No está implementado y de los más probable no se implementará debido a que es un mensaje para sistemas con colas de recepción
            try:
                mensaje = self.rec_cancelar_solicitud(data)
            except Exception as ex:
                self.__resolver_cancelar(persona, ex)

        else:
            self.__resolver_mensaje_desconocido(persona, ValueError(f'Mensaje desconocido {len(data)} {data}'))

    def __expirar_tiempo(self, persona: Persona):
        """
        Retorna True si la conexión con la persona ya expiró. False si no
        """
        if time.time() - self.tiempos_personas[str(persona)] <= self.MAX_VIDA:
            return False

        logging.debug(f'La conexión con {persona} expiró')

        if str(persona) in self.recursos_parciales:
            self.recursos_parciales.pop(str(persona))

        if str(persona) in self.recursos_enviando:
            self.recursos_enviando.pop(str(persona))

        # Comunicamos a la persona que ya no nos interesa y que lo bloqueamos
        mensaje_bloquear = self.env_bloquear()
        self.conexión.enviar_mensaje(persona, mensaje_bloquear)
        persona.estoy_bloqueando = True

        mensaje_interes = self.env_sin_interes()
        self.conexión.enviar_mensaje(persona, mensaje_interes)
        persona.estoy_interesado = False

        # Lo volvemos a poner como el default
        persona.esta_interesado = False
        persona.esta_bloqueando = True

        return True

    def __resolver_desconocido(self, persona: Persona, ex: Exception):
        """
        Maneja errores de personas desconocidas
        """
        raise ErrorRecepción('...', persona, ex)

    def __resolver_tiempo(self, persona: Persona, ex: Exception):
        """
        Maneja errores de expiración de tiempo
        """
        raise ErrorRecepción('...', persona, ex)

    def __resolver_saludo(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recibir saludos
        """
        raise ErrorRecepción('saludo falló', persona, ex)

    def __resolver_mantener_viva(self, persona: Persona, ex: Exception):
        """
        Maneja errores de mantener viva
        """
        raise ErrorRecepción('mantener viva falló', persona, ex)

    def __resolver_bloquear(self, persona: Persona, ex: Exception):
        """
        Maneja errores de bloquear
        """
        raise ErrorRecepción('bloquear falló', persona, ex)

    def __resolver_desbloquear(self, persona: Persona, ex: Exception):
        """
        Maneja errores de desbloquear
        """
        raise ErrorRecepción('desbloquear falló', persona, ex)

    def __resolver_interesado(self, persona: Persona, ex: Exception):
        """
        Maneja errores de interesado
        """
        raise ErrorRecepción('interesado falló', persona, ex)

    def __resolver_sin_interes(self, persona: Persona, ex: Exception):
        """
        Maneja errores de sin interés
        """
        raise ErrorRecepción('sin interés falló', persona, ex)

    def __resolver_existe(self, persona: Persona, ex: Exception):
        """
        Maneja errores de existe-pieza
        """
        raise ErrorRecepción('existe falló', persona, ex)

    def __resolver_listar(self, persona: Persona, ex: Exception):
        """
        Maneja errores de listar piezas
        """
        raise ErrorRecepción('listar falló', persona, ex)

    def __resolver_solicitar_pieza(self, persona: Persona, ex: Exception):
        """
        Maneja errores de solicitar pieza
        """
        # Bloqueamos a la personas
        mensaje = self.env_bloquear()
        self.conexión.enviar_mensaje(persona, mensaje)
        persona.estoy_bloqueando = True

        raise ErrorRecepción('solicitar pieza falló', persona, ex)

    def __resolver_recibir_pieza(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recibir pieza
        """
        # Desinteresamos a la persona
        mensaje = self.env_sin_interes()
        self.conexión.enviar_mensaje(persona, mensaje)
        persona.estoy_interesado = False

        raise ErrorRecepción('recibir pieza falló', persona, ex)

    def __resolver_cancelar(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recibir cancelar
        """
        raise ErrorRecepción('recibir cancelar falló', persona, ex)

    def __resolver_mensaje_desconocido(self, persona: Persona, ex: Exception):
        """
        Maneja mensajes desconocidos
        """
        raise ErrorRecepción('...', persona, ex)

    #handshake
    def rec_saludo(self, mensaje_recibido):
        """
        handshake: <pstrlen><pstr><reserved><info_hash><peer_id>

        info_hash: sha1 hash de 20 bytes
        peer_id  : 20 bytes en el formato Azureus 
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 68:
            raise TypeError("Este mensaje no tiene la dimensión de un saludo")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "saludo"
        dic_mensaje['largo_protocolo']  = struct.unpack_from("!B", mensaje_recibido, offset=0)[0]
        dic_mensaje['protocolo']        = str(mensaje_recibido[1:20], encoding  = 'utf-8')
        dic_mensaje['bytes_reservados'] = mensaje_recibido[20:28]
        dic_mensaje['info_hash']        = mensaje_recibido[28:48]
        dic_mensaje['id_persona']     = str(mensaje_recibido[48:], encoding   = 'utf-8')
        return dic_mensaje


    def env_saludo(self, peer_id, info_hash):
        """
        handshake: <pstrlen><pstr><reserved><info_hash><peer_id>

        info_hash: sha1 hash de 20 bytes, es el identificador del recurso a
                   compartir por la comuna, así cómo para saber de que
                   estamos hablando.

        peer_id  : 20 bytes en el formato Azureus 
        """
        protocolo        = "BitTorrent protocol"
        largo_protocolo  = struct.pack("!B", 19) # pasa el 19 a un byte (big endian)
        bytes_reservados = struct.pack("!Q", 0)  # pasa el 0 a 8 bytes

        saludo = largo_protocolo + \
                bytes(protocolo, 'utf-8') +\
                bytes_reservados +\
                info_hash +\
                bytes(peer_id, 'utf-8')

        # El send lo va a manejar la conexión y no el protocolo.
        return saludo

    #keep-alive
    def rec_mantener_viva(self, mensaje_recibido):
        """
        keep-alive: <len=0000>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 4:
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: mantener-viva")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "mantener-viva"

        return dic_mensaje

    def env_mantener_viva(self) :
        """
        keep-alive: <len=0000>
        """
        largo_mensaje =  struct.pack(">I", 0)  # Pasa el 0 a 4 bytes

        # El send lo va a manejar la conexión y no el protocolo.
        return largo_mensaje

    #choke
    def rec_bloquear(self, mensaje_recibido):
        """
        choke: <len=0001><id=0>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 5:
            print(mensaje_recibido)
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: bloquear")

        if int(mensaje_recibido[4]) != 0:
            raise TypeError("Este mensaje no es un mensaje: bloquear")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "bloquear"

        return dic_mensaje

    def env_bloquear(self):
        """
        choke: <len=0001><id=0>
        """
        largo_mensaje =  struct.pack("!I", 1)  # Pasa el 0 a 4 bytes
        tipo_mensaje  =  struct.pack("!B", 0)  # Pasa el 0 a 1 byte

        mensaje = largo_mensaje +\
                    tipo_mensaje

        # El send lo va a manejar la conexión y no el protocolo.
        return mensaje

    #unchoke
    def rec_desbloquear(self, mensaje_recibido):
        """
        unchoke: <len=0001><id=1>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 5:
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: desbloquear")

        if int(mensaje_recibido[4]) != 1:
            raise TypeError("Este mensaje no es un mensaje: bloquear")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "desbloquear"

        return dic_mensaje

    def env_desbloquear (self):
        """
        unchoke: <len=0001><id=1>
        """
        largo_mensaje = struct.pack("!I", 1)
        tipo_mensaje  = struct.pack("!B", 1)

        mensaje = largo_mensaje +\
                    tipo_mensaje

        # El send lo va a manejar la conexión y no el protocolo.
        return mensaje

    #interested
    def rec_interesado(self, mensaje_recibido):
        """
        interested: <len=0001><id=2>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 5:
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: interesado")

        if int(mensaje_recibido[4]) != 2:
            raise TypeError("Este mensaje no es un mensaje: interesado")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "interesado"

        return dic_mensaje

    def env_interesado(self):
        """
        interested: <len=0001><id=2>
        """
        largo_mensaje = struct.pack("!I", 1) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 2) # Pasa el 2 a 1 byte

        mensaje = largo_mensaje +\
                    tipo_mensaje

        # El send lo va a manejar la conexión y no el protocolo.
        return mensaje

    #not interested
    def rec_sin_interes(self, mensaje_recibido):
        """
        not interested: <len=0001><id=3>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 5:
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: sin-interes")

        if int(mensaje_recibido[4]) != 3:
            raise TypeError("Este mensaje no es un mensaje: sin-interes")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "sin-interes"

    def env_sin_interes(self):
        """
        not interested: <len=0001><id=3>
        """
        largo_mensaje = struct.pack("!I", 1) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 3) # Pasa el 3 a 1 byte

        mensaje = largo_mensaje +\
                    tipo_mensaje


        # El send lo va a manejar la conexión y no el protocolo.
        return mensaje

    #have
    def rec_existe(self, mensaje_recibido):
        """
        have: <len=0005><id=4><piece index>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 5:
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: existe")

        if int(mensaje_recibido[4]) != 4:
            raise TypeError("Este mensaje no es un mensaje: existe")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "existe"
        dic_mensaje['índice_pieza']     = struct.unpack("!I", mensaje_recibido[6:], offset=6)[0]

        return dic_mensaje

    def env_existe(self, índice_pieza):
        """
        have: <len=0005><id=4><piece index>
        """
        largo_mensaje = struct.pack("!I", 1) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 4) # Pasa el 4 a 1 byte

        mensaje = largo_mensaje +\
                tipo_mensaje +\
                bytes(índice_pieza, 'utf-8')

        # El send lo va a manejar la conexión y no el protocolo.
        return mensaje

    #bitfield
    def rec_listar(self, mensaje_recibido):
        """
        bitfield: <len=0001+X><id=5><bitfield>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 5:
            raise TypeError("Este mensaje no es un mensaje: listar")

        largo_mensaje = struct.unpack("!I", mensaje_recibido[0:4])[0]

        if largo_mensaje != len(mensaje_recibido[5:]) + 1:
            raise TypeError("El campo de largo de mensaje no corresponde con los datos recibidos")

        # toma los bytes y los combierte a un arreglo de bits
        listado_piezas = BitArray(mensaje_recibido[5:]) 
        
        cantidad = 0
        for i in listado_piezas:
            if i == 1:
                cantidad+=1

        logging.debug(f'<<< Se recibe la lista de piezas {listado_piezas}')
        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "listado"
        dic_mensaje['cantidad']         = cantidad
        dic_mensaje['listado']          = listado_piezas

        return dic_mensaje


    def env_listar(self, recurso: Recurso):
        """
        bitfield: <len=0001+X><id=5><bitfield>

        recurso_local: Es el archivo torrent que crea un recurso "vacío"
        recurso_remoto: Es el archivo torrent que crea un recurso remoto y
                        completa esta lista con lo que aparece en la sección
                        de piezas del par
        """

        # Lo paso a bytes
        lista_bits = recurso.piezas.tobytes()
        # Pasa la cantidad de bytes en la lista a 4 bytes
        largo_mensaje = struct.pack("!I", 1+len(lista_bits)) 
        tipo_mensaje  = struct.pack("!B", 5) # Pasa el 5 a 1 byte

        mensaje = largo_mensaje +\
                tipo_mensaje +\
                lista_bits
        # El send lo va a manejar la conexión y no el protocolo.
        return mensaje

    #request
    def rec_solicitar(self, mensaje_recibido):
        """
        request: <len=0013><id=6><index><begin><length>
        """

        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 6:
            raise TypeError("Este mensaje no es un mensaje: solicitar")

        if len(mensaje_recibido[4:]) != 13:
            raise TypeError("Este mensaje no tiene la dimensión de un mensaje: solicitar")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']          = "solicitar"
        dic_mensaje['índice_pieza']  = struct.unpack("!I", mensaje_recibido[5:9])[0]
        dic_mensaje['byte_inicial']   = struct.unpack("!I", mensaje_recibido[9:13])[0]
        dic_mensaje['cantidad_bytes'] = struct.unpack("!I", mensaje_recibido[13:])[0]

        return dic_mensaje


    def env_solicitar(self, pieza, inicio, tamaño_bloque):
        """
        request: <len=0013><id=6><index><begin><length>

        pieza   : id (índice) de la pieza a traer
        inicio  : número de byte para iniciar dentro de la pieza
        cantidad: cantidad de bytes a solicitar
        """
        largo_mensaje = struct.pack("!I", 13) # Pasa el 1133 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 6) # Pasa el 6 a 1 byte

        índice_pieza = struct.pack("!I", pieza)
        byte_inicial = struct.pack("!I", inicio)
        cantidad_bytes = struct.pack("!I", tamaño_bloque)

        mensaje = largo_mensaje +\
                    tipo_mensaje +\
                    índice_pieza +\
                    byte_inicial +\
                    cantidad_bytes

        return mensaje

    #piece
    def rec_pieza(self, mensaje_recibido):
        """
        piece: <len=0009+X><id=7><index><begin><block>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 7:
            raise TypeError("Este mensaje no es un mensaje: pieza")

        largo_mensaje = struct.unpack("!I", mensaje_recibido[0:4])[0]

        if largo_mensaje != len(mensaje_recibido[4:]):
            raise TypeError("El campo de largo de mensaje no corresponde con los datos recibidos")


        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']          = "pieza"
        dic_mensaje['índice_pieza']  = struct.unpack("!I", mensaje_recibido[5:9])[0]
        dic_mensaje['byte_inicial']   = struct.unpack("!I", mensaje_recibido[9:13])[0]
        dic_mensaje['bloque'] = mensaje_recibido[13:]

        return dic_mensaje


    def env_pieza(self, pieza, inicio, bloque: bytes):
        """
        piece: <len=0009+X><id=7><index><begin><block>

        pieza   : id de la pieza a traer
        inicio  : número de byte para iniciar dentro de la pieza
        bloque  : bloque de bytes a enviar 
        """
        largo_mensaje = struct.pack("!I", 9+len(bloque)) # Pasa el tamaño a 4 bytes
        tipo_mensaje  = struct.pack("!B", 7) # Pasa el 7 a 1 byte

        número_pieza = struct.pack("!I", pieza)
        byte_inicial = struct.pack("!I", inicio)

        mensaje = largo_mensaje +\
                    tipo_mensaje +\
                    número_pieza +\
                    byte_inicial +\
                    bloque

        return mensaje

    #cancel
    def rec_cancelar_solicitud(self, mensaje_recibido):
        """
        cancel: <len=0013><id=8><index><begin><length>
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 8:
            raise TypeError("Este mensaje no es un mensaje: cancelar")

        if len(mensaje_recibido) != 13: 
            raise TypeError("Este mensaje no tiene la dimensión de : cancelar")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']          = "cancelar"
        dic_mensaje['índice_pieza']  = struct.unpack("!I", mensaje_recibido[5:9])[0]
        dic_mensaje['byte_inicial']   = struct.unpack("!I", mensaje_recibido[9:13])[0]
        dic_mensaje['cantidad_bytes'] = struct.unpack("!I", mensaje_recibido[13:])[0]

        return dic_mensaje

    def env_cancelar_solicitud(self, pieza, inicio, tamaño_bloque):
        """
        cancel: <len=0013><id=8><index><begin><length>

        pieza   : id de la pieza a traer
        inicio  : número de byte para iniciar dentro de la pieza
        cantidad: cantidad de bytes a solicitar
        """
        largo_mensaje = struct.pack("!I", 13) # Pasa el 1133 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 8) # Pasa el 8 a 1 byte

        número_pieza = struct.pack("!I", pieza)
        byte_inicial = struct.pack("!I", inicio)
        cantidad_bytes = struct.pack("!I", tamaño_bloque)

        mensaje = largo_mensaje +\
                    tipo_mensaje +\
                    número_pieza +\
                    byte_inicial +\
                    cantida_bytes
        
        return mensaje



class ComitéRegistro():
    """
    Implementa el protocolo de comunicación entre varias personas
    involucradas en la comuna para transferir información de personas y recursos

    Una comuna es un conjunto de personas que comparten recursos.
    
    Nota: El protocolo solo va a formar y desarmar los mensajes.
        - Si envía un mensaje (métodos env_), retorna un bytes codificado utf-8
        - Si recibe un mensaje (métodos rec_), retorna un diccionario ordenado 
    """

    cerrando = False # Un parametro para indicar al sistema que se está parando el funcionamiento

    id_comuna                : str # el nombre de la comuna

    persona_local            : Persona # la persona local
    conexión                 : Conexión # la conexión
    personas_remotas         : [Persona] # las personas remotas
    nombres_personas_remotas : dict # los nombres asociado a las personas remotas
    tiempos_personas         : dict # los tiempos de última conexión de las personas
    persona_comité_recursos  : Persona # la persona del comité de recursos
    escucha                  : threading.Thread # el thread de envío y recepción de mensajes

    def __init__(self, id_comuna, persona, personas_remotas, nombres_personas_remotas, tiempos_personas, ip,  puerto =
            7896, datos_comité_recursos=None):
        """ 
        Genera el ID de la comuna (un texto de 20-bytes).
        """

        self.id_comuna = id_comuna

        self.persona_local = persona
        self.personas_remotas = personas_remotas
        
        self.nombres_personas_remotas = nombres_personas_remotas

        self.persona_comité_recursos = Persona(*datos_comité_recursos)

        self.conexión = Conexión((ip, puerto))

        self.tiempos_personas = tiempos_personas

        self.escucha = threading.Thread(target=self.iniciar_escucha)
        self.escucha.start()

        logging.debug(f'Comité de registro inicializado en puerto {puerto}')

    def iniciar_escucha(self):
        """
        Inicializa la escucha permanente para este protocolo
        """

        # Recibir - Procesar - Responder
        while True:
            # Este try captura los errores de recepción
            try:
                # Este try captura cuando el socket se cierra
                try:
                    # Recibimos el mensaje
                    mensaje_recibido, persona = self.conexión.recibir_mensaje()
                except OSError as ex:
                    if self.cerrando:
                        break
                    logging.exception(f'Ocurrió una excepción OSError en la recepción de información')
                    raise ex

                # Procesamos el mensaje
                mensaje_respuesta = self.procesar_mensaje(mensaje_recibido, persona)
  
                # Reenvía el mensaje de respuesta
                if mensaje_respuesta != None:
                    self.conexión.enviar_mensaje(persona, mensaje_respuesta)

            except ErrorRecepción as ex:
                logging.exception('Ocurrió un error cuando se recibió un mensaje')

                if ex.crítico:
                    logging.critical('El error de recepción es crítico!')
                    raise ex

    def cerrar_escucha(self):
        """
        Para el programa
        """
        logging.debug('Cerrando comité de registro')

        self.cerrando = True
        self.conexión.cerrar_conexión()
        self.escucha.join()

    def solicitar_personas(self):
        """
        Envía un saludo a todas las personas registradas
        (para que estas respondan con una lista de recursos: [info_hash, info_hash, ...])

        """
        logging.debug(f' Enviando saludo a lista de personas {self.personas_remotas}')

        # Crea un mensaje de saludo para solicitar registros
        mensaje = self.env_saludo(self.id_comuna, bytes([0]*20))

        for persona_remota in self.personas_remotas:

            # Envía solicitudes de listas solo a las comunas
            if persona_remota.comuna == True:
                logging.debug(f'$ Solicitando registros a la comuna {persona_remota}')
                self.conexión.enviar_mensaje(persona_remota, mensaje)


    def solicitar_recursos(self, persona):
        """
        Solicita los recursos una persona
        """
        mensaje = self.env_listar(persona)
        self.conexión.enviar_mensaje(persona, mensaje)

    def solicitar_detalle_recurso(self, persona, info_hash):
        """
        Solicita los recursos una persona
        """
        mensaje = self.env_solicitud_detalle(info_hash)
        self.conexión.enviar_mensaje(persona, mensaje)

    def registrar_comuna(self, persona: Persona):
        """
        Registra una persona tipo comuna en la lista de personas
        """
        self.personas_remotas.append(persona)
        self.nombres_personas_remotas[str(persona)] = persona


    # Wire protocol
    def procesar_mensaje(self, data, persona):
        """
        Este es el método con el protocolo funcionando en conjunto
        """
        logging.debug(f'Procesando mensaje recibido {data} {persona}')

        if len(data) == 68: # Saludo

            ## Verifico si recibí un saludo
            try:
                mensaje_recibido = self.rec_saludo(data)
            except Exception as ex:
                self.__resolver_saludo(persona, ex)

            if self.id_comuna[1:7] != mensaje_recibido['id_persona'][1:7]:
                self.__resolver_saludo(persona, TypeError(f"El cliente de {persona} es {mensaje_recibido['id_persona'][1:7]}. Esta versión no es compatible con el cliente actual {self.id_comuna[1:7]}"))

            # Envío la lista de personas sin recursos
            logging.debug(f'>>> enviando personas a: {persona}')
            mensaje_respuesta = self.env_personas()

            if str(persona) not in self.nombres_personas_remotas:
                self.personas_remotas.append(persona)
                self.nombres_personas_remotas[str(persona)] = persona
                self.tiempos_personas[str(persona)] = time.time()
                persona.comuna = True

            return mensaje_respuesta

        elif data[4] == 0: # Lista de personas
            if str(persona) not in self.nombres_personas_remotas:
                self.__resolver_personas_desconocida(persona, ValueError(f'{persona} no se reconoce'))

            try:
                mensaje = self.rec_personas(data)
            except Exception as ex:
                self.__resolver_personas(persona, ex)

            for persona_remota in mensaje['personas']:
                if persona_remota not in self.personas_remotas:
                    logging.debug(f'<<< Persona recibida {persona_remota}')

                    # Por si la persona tiene un ip relativo a una máquina
                    if persona_remota.ip == '127.0.0.1':
                        logging.debug(f'La persona tiene ip de máquina local, entonces se le asigna el ip de su proveedor: {persona.ip}')
                        persona_remota.ip = persona.ip

                    # La agregamos
                    self.personas_remotas.append(persona_remota)
                    self.nombres_personas_remotas[str(persona_remota)] = persona_remota
                    self.tiempos_personas[str(persona_remota)] = time.time()


        elif data[4] == 1: # Lista de recursos
            if str(persona) not in self.nombres_personas_remotas:
                self.__resolver_personas_desconocida(persona, ValueError(f'{persona} no se reconoce'))

            logging.debug(f'<<< Recibiendo lista de recursos {data}')

            try:
                mensaje = self.rec_recursos(data, persona)
            except Exception as ex:
                self.__resolver_recursos(persona, ex)

            persona = self.nombres_personas_remotas[str(persona)]

            # Agregamos el recurso a la personas
            for recurso in mensaje['recursos']:
                if not self.__es_recurso_duplicado(persona.recursos, recurso):
                    persona.recursos.append(recurso)

        elif data[4] == 2: # Listar recursos
            try:
                mensaje = self.rec_listar(data)
            except Exception as ex:
                self.__resolver_listar(persona, ex)

            mensaje_respuesta = self.env_recursos()

            return mensaje_respuesta

        elif data[4] == 3: # Detalle de un recurso
            if str(persona) not in self.nombres_personas_remotas:
                self.__resolver_personas_desconocida(persona, ValueError(f'{persona} no se reconoce'))

            try:
                mensaje = self.rec_detalle(data, persona)
            except Exception as ex:
                self.__resolver_recibir_detalle(persona, ex)

            logging.debug(f'Procesando el detalle del recurso: {mensaje}')

            if mensaje['info_hash'] != Recurso().crear_info_hash(mensaje['atributos']):
                self.__resolver_recibir_detalle(persona, ValueError(f"info_hash incorrecto {mensaje['info_hash']}"))

            # Guarda la información sobre el recurso
            for persona_remota in self.personas_remotas:

                if persona_remota.comuna == True:
                    for recurso in persona_remota.recursos:
                        if recurso.info_hash == mensaje['info_hash']:
                            recurso.atributos = mensaje['atributos']
                            return


        elif data[4] == 4: # Solicitud de detalle

            try:
                mensaje = self.rec_solicitud_detalle(data, persona)
            except Exception as ex:
                self.__resolver_solicitud_detalle(persona, ex)

            logging.debug(f'Se recibe una solicitud de detalle: {mensaje}')

            # Busca el recurso y le manda el detalle
            for recurso in self.persona_local.recursos:
                if recurso.info_hash == mensaje['info_hash']:
                    mensaje_respuesta = self.env_detalle(recurso)
                    return mensaje_respuesta

        else: 
            self.__resolver_mensaje_desconocido(persona, ValueError(f'Mensaje desconocido {len(data)} {data}'))

    def __resolver_persona_desconocida(self, persona: Persona, ex: Exception):
        """
        Maneja errores con personas desconocidas
        """
        raise ErrorRecepción('...', persona, ex)

    def __resolver_saludo(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recibir saludos
        """
        raise ErrorRecepción('saludo falló', persona, ex)

    def __resolver_personas(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recepción de la lista de personas
        """
        raise ErrorRecepción('recibir personas falló', persona, ex)

    def __resolver_recursos(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recibir recursos
        """
        raise ErrorRecepción('recibir recursos falló', persona, ex)

    def __resolver_listar(self, persona: Persona, ex: Exception):
        """
        Maneja errores de mandar recursos
        """
        raise ErrorRecepción('mandar recursos falló', persona, ex)

    def __resolver_recibir_detalle(self, persona: Persona, ex: Exception):
        """
        Maneja errores de recibir detalles sobre recursos
        """
        raise ErrorRecepción('recibir detallé de recurso falló', persona, ex)

    def __resolver_solicitud_detalle(self, persona: Persona, ex: Exception):
        """
        Maneja errores de mandar detalles sobre recursos
        """
        raise ErrorRecepción('mandar detallé de recurso falló', persona, ex)

    def __resolver_mensaje_desconocido(self, persona: Persona, ex: Exception):
        """
        Maneja errores de mensajes desconocidos
        """
        raise ErrorRecepción('...', persona, ex)

    def rec_saludo(self, mensaje_recibido):
        """
        handshake: <pstrlen><pstr><reserved><info_hash><peer_id>

        info_hash: sha1 hash de 20 bytes
        peer_id  : 20 bytes en el formato Azureus 
        """
        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if len(mensaje_recibido) != 68:
            raise TypeError("Este mensaje no tiene la dimensión de un saludo")

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "saludo"
        dic_mensaje['largo_protocolo']  = struct.unpack_from("!B", mensaje_recibido, offset=0)[0]
        dic_mensaje['protocolo']        = str(mensaje_recibido[1:20], encoding  = 'utf-8')
        dic_mensaje['bytes_reservados'] = mensaje_recibido[20:28]
        dic_mensaje['info_hash']        = mensaje_recibido[28:48]
        dic_mensaje['id_persona']     = str(mensaje_recibido[48:], encoding   = 'utf-8')

        return dic_mensaje

    def env_saludo(self, id, info_hash):
        """
        handshake: <pstrlen><pstr><reserved><info_hash><peer_id>

        info_hash: sha1 hash de 20 bytes, es el identificador del recurso a
                   compartir por la comuna, así cómo para saber de que
                   estamos hablando.

        peer_id  : 20 bytes en el formato Azureus 
        info_hash: 20 bytes en ceros
        """
        protocolo        = "BitTorrent protocol"
        largo_protocolo  = struct.pack("!B", 19) # pasa el 19 a un byte (big endian)
        bytes_reservados = struct.pack("!Q", 0)  # pasa el 0 a 8 bytes

        saludo = largo_protocolo + \
                bytes(protocolo, 'utf-8') +\
                bytes_reservados +\
                info_hash +\
                bytes(self.id_comuna, 'utf-8')

        # El send lo va a manejar la conexión y no el protocolo.
        return saludo

    def rec_personas(self, mensaje_recibido):
        """
        Recibe una lista de personas
        recursos: <len=0005+6*X><id=0><person_list>

        donde X número de personas
        """
        logging.debug(f'Se recibe la lista de personas. mensaje_recibido {mensaje_recibido}')


        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 0:
            raise TypeError("Este mensaje no es un mensaje: personas")
        

        lista_personas = []

        for índice in range(5, len(mensaje_recibido), 7):

            tipo_persona = mensaje_recibido[índice]

            ip = inet_ntoa( bytearray(mensaje_recibido[1+índice:índice+5]))
            puerto = struct.unpack(">H", mensaje_recibido[índice+5:índice+7])[0]

            nueva_persona = Persona(ip, puerto)

            if str(nueva_persona) == str(self.persona_local) or str(nueva_persona) == str(self.persona_comité_recursos):
                 continue

            nueva_persona.comuna = tipo_persona

            # retorna la persona que existe o una nueva
            nueva_persona = self.__retornar_persona_duplicada(nueva_persona)
            logging.debug(f'La persona nueva es: {nueva_persona}')

            lista_personas.append(nueva_persona)

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']             = "personas"
        dic_mensaje['personas']     = lista_personas

        return dic_mensaje

    def env_personas(self):
        """
        Envía una lista de personas remotas (contactos) disponibles
        recursos: <len=0005+7*X><id=0><person_list>

        person_list = <id><ip><port>
                        1   4     2 

        donde X número de personas
        """
        logging.debug(f'Se envía la lista de personas')


        lista_personas=[]

        for persona_remota in self.personas_remotas + [self.persona_comité_recursos]:
            
            # Indica si el contacto es comuna o comité
            tipo_persona  = struct.pack("!B", 0) 
            if persona_remota.comuna == True:
                tipo_persona  = struct.pack("!B", 1) 

            # Pasa la información a bytes
            ip = inet_aton(persona_remota.ip)
            port = struct.pack(">H", int(persona_remota.puerto))

            lista_personas.append(tipo_persona+ip + port)

        largo_mensaje = struct.pack("!I", 5+7*len(self.personas_remotas)) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 0) # Pasa el 4 a 1 byte

        # Arma el mensaje a enviar
        mensaje = largo_mensaje +\
                  tipo_mensaje +\
                  b''.join(lista_personas)

        return mensaje

    def rec_recursos(self, mensaje_recibido, persona):
        """
        Recibe una lista recursos
        recursos: <len=0005+20*X><id=1><resource_list>

        donde X número de recursos
        """

        logging.debug(f'Se recibe la lista de recuros {mensaje_recibido}')

        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 1:
            raise TypeError("Este mensaje no es un mensaje: recursos")

        lista_recursos = []

        for índice in range (5, len(mensaje_recibido), 20):

            info_hash = mensaje_recibido[índice:índice+20]

            nuevo_recurso = Recurso(info_hash=info_hash)
            lista_recursos.append(nuevo_recurso)

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']       = "recursos"
        dic_mensaje['persona']    = persona
        dic_mensaje['recursos']   = lista_recursos

        return dic_mensaje


    def env_recursos(self):
        """
        Recibe una lista recursos
        recursos: <len=0005+20*X><id=1><resource_list>

        donde X número de recursos
        """
        logging.debug(f'Se envía la lista de recursos')

        lista_recursos=[]

        # Toma los recursos disponibles en la persona local o comuna
        for recurso in self.persona_local.recursos:
            lista_recursos.append(recurso.info_hash)

        largo_mensaje = struct.pack("!I", 5+20*len(lista_recursos)) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 1) # Pasa el 4 a 1 byte

        mensaje = largo_mensaje +\
                tipo_mensaje +\
                b''.join(lista_recursos)
                
        return mensaje

    def rec_listar(self, mensaje_recibido):
        """
        recibe una solicitud para listar recursos

        solicitar recursos: <len=0005><id=2>>
        """

        logging.debug(f' <<< Se recibe la lista de recuros')

        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 2:
            raise TypeError("Este mensaje no es un mensaje: recursos")

        lista_recursos = []


        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']       = "listar_recursos"

        return dic_mensaje

    def env_listar(self, persona):
        """
        Envía una solicitud para listar recursos

        solicitar recursos: <len=0005><id=2>>

        """

        logging.debug(f'Se genera una solicitud de recursos')

        largo_mensaje = struct.pack("!I", 5) # Pasa el 5 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 2) # Pasa el 2 a 1 byte

        mensaje = largo_mensaje +\
                  tipo_mensaje

        return mensaje


    def __retornar_persona_duplicada(self, nueva_persona: Persona):
        """
        Retorna la persona si está duplicada o False si es una nueva persona
        """

        if str(nueva_persona) in self.nombres_personas_remotas:
            return self.nombres_personas_remotas[str(nueva_persona)]

        return nueva_persona 

    def __es_recurso_duplicado(self, lista_recursos, nuevo_recurso):
        """
        Retorna la persona si está duplicada o False si es una nueva persona
        """

        for recurso in lista_recursos:
            if recurso.info_hash == nuevo_recurso.info_hash:
                return True 

        return False
        
    def rec_detalle(self, mensaje_recibido, persona):
        """
        Recibe una detalle de recurso
        recursos: <len=0005+X><id=3><info_hash><encoded atributes>

        donde X bytes del mensaje
        """

        logging.debug(f'Se recibe la lista de recuros {mensaje_recibido}')

        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 3:
            raise TypeError("Este mensaje no es un mensaje: recursos")

        
        info_hash = mensaje_recibido[5:25]

        encoder=bencodepy.Bencode(encoding='utf-8', dict_ordered=False)
        atributos = encoder.decode(mensaje_recibido[25:])


        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']       = "detalle_recurso"
        dic_mensaje['info_hash']  = info_hash
        dic_mensaje['atributos']  = atributos

        return dic_mensaje


    def env_detalle(self, recurso):
        """
        Envía el detalle de un recurso
        recursos: <len=0005+X><id=3><info_hash><encoded atributes>

        donde X bytes del mensaje
        """
        logging.debug(f'Se envía detalle del recurso {recurso.info_hash}')

        atributos = recurso.atributos_formato_bencoded()

        largo_mensaje = struct.pack("!I", 25+len(atributos)) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 3) # Pasa el 4 a 1 byte

        mensaje = largo_mensaje +\
                tipo_mensaje +\
                recurso.info_hash +\
                atributos 
                
        return mensaje

    def rec_solicitud_detalle(self, mensaje_recibido, persona):
        """
        Recibe una solicitud de detalle de recurso 
        recursos: <len=00025><id=4><info_hash>

        donde X bytes del mensaje
        """

        logging.debug(f'Se recibe la lista de recuros {mensaje_recibido}')

        if type(mensaje_recibido) != bytes:
            raise TypeError("El mensaje debe ser de tipo bytes")

        if int(mensaje_recibido[4]) != 4:
            raise TypeError("Este mensaje no es un mensaje: recursos")

        
        info_hash = mensaje_recibido[5:25]

        dic_mensaje = OrderedDict()
        dic_mensaje['tipo']       = "solicitud_detalle"
        dic_mensaje['info_hash']  = info_hash

        return dic_mensaje


    def env_solicitud_detalle(self, info_hash):
        """
        Envía el detalle de un recurso
        recursos: <len=0025><id=4><info_hash>

        donde X bytes del mensaje
        """
        logging.debug(f'Se solicita detalle de recurso con info_hash {info_hash}')

        largo_mensaje = struct.pack("!I", 25) # Pasa el 1 a 4 bytes
        tipo_mensaje  = struct.pack("!B", 4) # Pasa el 4 a 1 byte

        mensaje = largo_mensaje +\
                tipo_mensaje +\
                info_hash 
                
        return mensaje


class ErrorRecepción(Exception):
    """
    Clase de error para manejar los problemas que ocurren en momento de recepción de información.
    """
    ex      : Exception # La excepción en sí
    persona : Persona # La persona que lo causó
    mensaje : str # El mensaje asociado
    crítico = False # Si es crítico

    def __init__(self, mensaje: str, persona: Persona, ex: Exception, *args):
        super().__init__(args)

        self.ex = ex
        self.persona = persona
        self.mensaje = mensaje

    def __str__(self):
        if self.crítico:
            return f'Ocurrió un error crítico con persona {self.persona} >>> {self.mensaje} >>> {type(self.ex).__name__}: {self.ex}'
        return f'Persona {self.persona} provocó un error >>> {self.mensaje} >>> {type(self.ex).__name__}: {self.ex}'
