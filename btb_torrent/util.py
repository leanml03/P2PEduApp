# Determina si dos IPs pueden ser punteadas por hueco.
import ipaddress
import socket

"""
Rangos de direcciónes de IP privadas

192.168.0.0 - 192.168.255.255 
172.16.0.0 - 172.31.255.255 
10.0.0.0 - 10.255.255.255
"""


ipaddress.ip_address(ip).is_private
ipaddress.ip_address(ip).is_global


# Enviar mensaje a todas las direcciones públicas de la lista de direcciones para inicializar el hole punching

def abrir_campo(direcciones: list):
    """
    Envía un mensaje dummy a cada dirección pública
    """

    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP

    for dirección, puerto in direcciones:
        
        if ipaddress.ip_address(dirección).is_global():
            print("--------------->", dirección)
            sock.sendto(b'0', (dirección, puerto))

def probar_nat():
    """
    Un código para probar NAT (sacado del internet)
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.settimeout(1)

    sock.sendto(b'hello', ('natcheck.sctp.org', 8888))

    try:
        data, address = sock.recvfrom(1024)
    except socket.timeout:
        print('Tipo de NAT: symmetric')
        return

    if data == b'full cone':
        print('Tipo de NAT: full cone')
    elif data == b'restricted cone':
        print('Tipo de NAT: restricted cone')
    elif data == b'port restricted':
        print('Tipo de NAT type: port restricted')
    else:
        print('Tipo de NAT: desconocido')

    socket.close()
