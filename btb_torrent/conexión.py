from btb_torrent.persona import Persona

import socket
import threading


class Conexión():

    socket = None
    origen  = ()

    def __init__(self, origen: (str, int)):
        """ 
        Inicializa el puerto de escucha para recibir mensajes
        """

        # Accept UDP datagrams, on the given port, from any sender
        self.origen = origen
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Para poder reutilizar el mismo puerto
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("", self.origen[1]))

    def cerrar_conexión(self):
        """
        Cierra la conexión
        """
        self.socket.close()

    def enviar_mensaje(self, destino: Persona, mensaje = 'probando probando...'):
        """
        Envia un mensaje a una persona destino
        """

        self.socket.sendto(mensaje, (destino.ip, destino.puerto))

    def recibir_mensaje(self):
        """
        Recibe un mensaje en el puerto designado para escucha
        """
        # 16384 16K
        mensaje, dirección = self.socket.recvfrom(17408) # 17KB
        return (mensaje, Persona(*dirección))

    def recibir_paquete(self, enviador: Persona):
        """
        Recibe un paquete de una persona en el puerto designado para escucha
        """
        paquete, dirección = self.socket.recvfrom(enviador.puerto)
        return (paquete, Persona(*dirección))
