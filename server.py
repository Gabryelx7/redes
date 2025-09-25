import socket
import os
import hashlib
import struct
import math

HOST = '0.0.0.0'
PORT = 9999
BUFFER_SIZE = 2048
PAYLOAD_SIZE = 1400 # MTU = 1500 bytes

# --- Tipos de mensagens de protocolo ---
REQ = 0
DATA = 1
NACK = 2
INFO = 3
ERR = 4
ACK = 5

# --- Formato do Header ---
# ! = Ordenação big-endian para rede
# I = unsigned int (4 bytes)
# 16s = string de 16 bytes (para o MD5)
# B = unsigned char (1 byte)
HEADER_FORMAT = '!II16sB'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def create_header(seq_num, total_segments, checksum, msg_type):
  """Empacota os campos do header em um objeto bytes."""
  return struct.pack(HEADER_FORMAT, seq_num, total_segments, checksum, msg_type)

def unpack_header(packet):
  """Desempacota o header de um pacote recebido."""
  return struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])

def calculate_md5(data):
  """Calcula o hash MD5 para um chunk de dados."""
  return hashlib.md5(data).digest()

def main():
  """Função main para rodar o servidor UDP."""

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.bind((HOST, PORT))
  print(f"Servidor escutando em {HOST}:{PORT}")

  while True:
    print("\nEsperando por um novo cliente...")
    try:
      # Espera pela requisição de arquivo
      request, client_address = sock.recvfrom(BUFFER_SIZE)
      
      # Supõe que a solicitação está no formato "GET /filename.ext"
      filename = request.decode().strip().split(' ')[1][1:]
      print(f"solicitação de arquivo '{filename}' recebida de {client_address}")

      # Verifica se o arquivo existe
      if not os.path.exists(filename):
        print(f"Arquivo não encontrado: {filename}")
        error_header = create_header(0, 0, b'\x00'*16, ERR)
        error_message = b"Arquivo nao encontrado"
        sock.sendto(error_header + error_message, client_address)
        continue

      # Lê o arquivo existente
      with open(filename, 'rb') as f:
        file_content = f.read()

      file_size = len(file_content)
      total_segments = math.ceil(file_size / PAYLOAD_SIZE)
      full_file_md5 = calculate_md5(file_content)
      
      print(f"  - Tamanho do arquivo: {file_size / 1024:.2f} KB")
      print(f"  - Número de segmentos: {total_segments}")
      print(f"  - Hash MD5: {full_file_md5.hex()}")

      # Manda um pacote de informoções com os metadados (header e hash MD5)
      info_header = create_header(0, total_segments, b'\x00'*16, INFO)
      sock.sendto(info_header + full_file_md5, client_address)
      print("Pacote de metadados enviado para o cliente.")

      # Manda todos os pacotes de dados
      print("Iniciando transferência do arquivo...")
      for i in range(total_segments):
        start = i * PAYLOAD_SIZE
        end = start + PAYLOAD_SIZE
        chunk = file_content[start:end]
        chunk_md5 = calculate_md5(chunk)
        
        data_header = create_header(i, total_segments, chunk_md5, DATA)
        sock.sendto(data_header + chunk, client_address)

      print("Transferência completada.")

      # Lida com o processo de retransmissão dos arquivos
      while True:
        try:
          sock.settimeout(10.0) # Espera 10s para uma resposta
          response, _ = sock.recvfrom(BUFFER_SIZE)
          _, _, _, msg_type = unpack_header(response)

          if msg_type == NACK:
            # O cliente está requerindo retransmissões
            missing_seqs_str = response[HEADER_SIZE:].decode()
            missing_seqs = [int(s) for s in missing_seqs_str.split(',')]
            print(f"NACK recebido para os segmentos: {missing_seqs}")

            for seq_num in missing_seqs:
              start = seq_num * PAYLOAD_SIZE
              end = start + PAYLOAD_SIZE
              chunk = file_content[start:end]
              chunk_md5 = calculate_md5(chunk)
              
              data_header = create_header(seq_num, total_segments, chunk_md5, DATA)
              sock.sendto(data_header + chunk, client_address)
            print(f"{len(missing_seqs)} pacotes foram reenviados.")

          elif msg_type == ACK:
            # Cliente confirmou a transferência
            print(f"O cliente {client_address} confirmou a transferência com sucesso de: '{filename}'.")
            break

        except socket.timeout:
          print(f"O cliente {client_address} expirou. Encerrando a conexão.")
          break
    except Exception as e:
      print(f"Ocorreu um erro: {e}")       


if __name__ == "__main__":
    main()