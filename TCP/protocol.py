import struct
import json
import hashlib

# Constantes do protocolo
HEADER_FORMAT = '!I'  # Ordem de bytes de rede (Big Endian), Unsigned Int
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
CHUNK_SIZE = 4096  # Blocos de 4KB para transferência de arquivos
ENC = "utf-8"

#------------------------------------------------------------------------------

def send_json(sock, data_dict):
    """Codifica um dicionário em JSON e envia com um prefixo de tamanho."""
    json_data = json.dumps(data_dict).encode(ENC)
    length_packed = struct.pack(HEADER_FORMAT, len(json_data))
    sock.sendall(length_packed + json_data)

#------------------------------------------------------------------------------

def receive_json(sock):
    """Lê um prefixo de tamanho e depois lê o conteúdo JSON."""
    header_data = recv_all(sock, HEADER_SIZE)
    if not header_data:
        return None
    
    msg_length = struct.unpack(HEADER_FORMAT, header_data)[0]
    payload_data = recv_all(sock, msg_length)
    if not payload_data:
        return None
        
    return json.loads(payload_data.decode(ENC))

#------------------------------------------------------------------------------

def recv_all(sock, n):
    """Auxiliar para garantir que recebemos exatamente n bytes (tratando fragmentação TCP)."""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

#------------------------------------------------------------------------------

def calculate_file_hash(filepath):
    """Calcula o SHA-256 de um arquivo."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Lê e atualiza o hash em blocos de 4KB
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

#------------------------------------------------------------------------------

def send_file(sock, filepath):
    """Envia bytes do arquivo em blocos."""
    with open(filepath, 'rb') as f:
        while True:
            bytes_read = f.read(CHUNK_SIZE)
            if not bytes_read:
                break
            sock.sendall(bytes_read)

#------------------------------------------------------------------------------

def receive_file_content(sock, filepath, filesize):
    """Recebe bytes do arquivo e os salva."""
    received = 0
    with open(filepath, 'wb') as f:
        while received < filesize:
            # Determina quanto ler (não ler além do final do arquivo)
            to_read = min(CHUNK_SIZE, filesize - received)
            chunk = recv_all(sock, to_read)
            if not chunk:
                raise Exception("Socket closed during file transfer")
            f.write(chunk)
            received += len(chunk)