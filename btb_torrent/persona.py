from bitstring import BitArray
from recurso import Recurso

class Persona: 

    identificador   : str

    ip              : str
    puerto          : int

    comuna          : bool 

    recursos        : list[Recurso]
    
    # Si un cliente quiere hablar con nosotros
    esta_interesado = False

    # Si el servidor me bloquea
    esta_bloqueando = True

    # Si estoy interesado
    estoy_interesado = False

    # Si estoy bloqueando
    estoy_bloqueando = True

    def __init__(self, ip=None, puerto=None, recurso=None):

        # inicializa datos internos
        self.ip = ip
        self.puerto = puerto
        self.recursos = []
        self.comuna = False

        if recurso != None:
            self.recursos.append(recurso)

    def agregar_recurso(self, recurso: Recurso):
        """
        La persona agrega un recurso a la comuna
        """
        self.recursos.append(recurso)

    def retornar_tupla_conexión(self):
        """
        Retorna la información de conexión según la necesitan los datos de
        sockets
        """
        return (self.ip, self.puerto)

    def __str__(self):

        return f'({self.ip},{self.puerto})'

    def __repr__(self):

        return f'({self.ip},{self.puerto})'
