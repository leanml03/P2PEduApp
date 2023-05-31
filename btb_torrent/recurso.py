from bitstring import BitArray
from hashlib import sha1, md5

import os
import bencodepy
import bencode


class Recurso: 

    nombre          : str
    piezas          : BitArray
    piezas_recibidas = 0
    ruta_en_disco   : str

    info_hash       : str
    atributos       : dict      # Infohash


    def __init__(self, ruta_completa: str = None, info_hash: str = None, atributos:dict = None ):
        """
        Crea un recurso para compartir con la comuna
        """
        self.atributos     = {}
        self.piezas        = None
        self.ruta_en_disco = None
        self.nombre        = None

        if ruta_completa != None:
            # En el caso de que esta sea un recurso introducido para compartir

            self.nombre = os.path.basename(ruta_completa)
            self.ruta_en_disco = ruta_completa

            self.__procesar_recurso()
            self.crear_archivo_meta_info()

        else:

            self.info_hash = info_hash


    def atributos_formato_bencoded(self):
        """
        Retorna el diccionario de atributos en formato bencoded para su
        transmisión

        Esto se almacenaría en la DHT para compartir la información y poder
        solicitar los recursos.
        """

        encoder=bencodepy.Bencode(encoding='utf-8', dict_ordered=False)
        return encoder.encode(self.atributos)

        
    def __procesar_recurso(self):
        """
        Procesa el archivo y genera la información para poder compartir el
        recurso con el resto de comunas a través de los comités.
        """

        with open(self.ruta_en_disco, 'rb') as archivo:
            contenido = archivo.read()

        # El mismo tamaño siempre TODO: Sacar esto de acá
        tamaño_pieza = 16384  # 16K

        # Divide el contenido del archivo en piezas y les da su propio sha1
        piezas_texto     = ''.join([ '1' for i in range(0, len(contenido), tamaño_pieza)])
        piezas_completas = [contenido[i:i + tamaño_pieza ] for i in range(0, len(contenido), tamaño_pieza)]
        piezas_sha1      = [ sha1(pieza).hexdigest() for pieza in piezas_completas ]


        # Completa la información que se comparte entre comunas sobre el
        # recurso disponible
        información = {}

        información["name"]         = self.nombre
        información["pieces"]       = ''.join(piezas_sha1)
	#información["pieces"]       = piezas_sha1
        información["md5sum"]       = md5(contenido).hexdigest()
        información["length"]       = len(piezas_sha1)
        información["piece length"] = tamaño_pieza

        # Información del recurso local
        self.piezas = BitArray(bin=piezas_texto)
        self.atributos["info"] = información
        self.atributos["nodes"] = []

        # Identificador único universal del recurso
        self.info_hash = self.crear_info_hash(self.atributos)

    def crear_info_hash(self, atributos: dict):
        """
        Crea el info_hash
        """
        return sha1(bencodepy.encode(atributos["info"])).digest()

    def crear_archivo_meta_info(self):
        """
        Crea un archivo metainfo a partir de los atributos
        """
        with open(self.nombre + ".vttorrent", 'wb') as archivo:
            archivo.write(self.atributos_formato_bencoded())

    def cargar_atributos(self, códigoben):
        """
        Carga los atributos a partir de un código ben
        """
        self.atributos = bencode.decode(códigoben)
        self.nombre = self.atributos["info"]["name"]
        self.info_hash = self.crear_info_hash(self.atributos)

    def cargar_archivo_meta_info(self, camino):
        """
        Carga un archivo de .vttorrent
        """
        with open(camino, 'r') as archivo:
            self.cargar_atributos(archivo.read())
