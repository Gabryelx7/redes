import socket
import struct
import hashlib
import re

BUFFER_SIZE = 2048
NACK_BATCH_SIZE = 150

# --- Tipos de mensagens de protocolo ---
REQ = 0
DATA = 1
NACK = 2
INFO = 3
ERR = 4
ACK = 5

# --- Formato do Header ---
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

def parse_address(user_input):
    """Processa entradas como '@127.0.0.1:9999/arquivo.txt'."""
    match = re.match(r"@([\d\.]+):(\d+)/(.+)", user_input)
    if match:
      return match.group(1), int(match.group(2)), match.group(3)
    return None, None, None

def main():
    """Função main para rodar o cliente UDP"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Recebe o endereço do servido e o arquivo
    while True:
      address_input = input("Digite o endereço do servidor e o arquivo (@IP:Port/filename): ")
      server_ip, server_port, filename = parse_address(address_input)
      if server_ip:
        break
      print("Formato invalido. Por favor use este formato: '@IP:Port/filename'.")
    
    server_address = (server_ip, server_port)

    # Recebe simulação de perdas de pacotes
    loss_input = input("Enter sequence numbers to drop (e.g., 5,8,12 or 'none'): ")
    packets_to_drop = set()
    if loss_input.lower() != 'none':
      try:
        packets_to_drop = {int(x.strip()) for x in loss_input.split(',')}
      except ValueError:
        print("Entrada inválida. Nenhum pacote será perdido.")
    
    # Faz a solicitação do arquivo
    request_message = f"GET /{filename}"
    sock.sendto(request_message.encode(), server_address)
    print(f"\nSolicitando arquivo '{filename}' de {server_address}...")

    # Espera o pacote de informações
    try:
      sock.settimeout(5.0)
      info_packet, _ = sock.recvfrom(BUFFER_SIZE)
      _, total_segments, _, msg_type = unpack_header(info_packet)
      
      if msg_type != INFO:
        if msg_type == ERR:
          error_msg = info_packet[HEADER_SIZE:].decode()
          print(f"Erro do servidor: {error_msg}")
        else:
          print(f"Erro no tipo de pacote recebido: {msg_type}. Abortando.")
        return  

      full_file_md5 = info_packet[HEADER_SIZE:]
      print(f"Pacote de informação recebido:")
      print(f"  - Número esperado de segmentos: {total_segments}")
      print(f"  - Hash MD5 do arquivo: {full_file_md5.hex()}")

    except socket.timeout:
      print("Servidor não respondeu à tempo")
      return
    
    # Prepara para a recepção de pacotes
    received_chunks = [None] * total_segments
    received_count = 0

    while received_count < total_segments:
      print("\n--- Iniciando a recepção ---")
        
      # Loop para receber um burst de pacotes
      while True:
        try:
          # Um timeout curto indica o fim do burst
          sock.settimeout(2.0)
          packet, _ = sock.recvfrom(BUFFER_SIZE)
          
          seq_num, _, checksum, msg_type = unpack_header(packet)
          
          if msg_type == DATA:
            # Simulação de perda
            if seq_num in packets_to_drop:
              print(f"Simulando perda do pacote {seq_num}")
              packets_to_drop.remove(seq_num)
              continue

            # Check de integridade
            payload = packet[HEADER_SIZE:]
            if calculate_md5(payload) != checksum:
              print(f"Pacote corrompido {seq_num}. Discartando.")
              continue
            
            # Guarda o pacote válido
            if received_chunks[seq_num] is None:
              received_chunks[seq_num] = payload
              received_count += 1
            
            print(f"\r{received_count}/{total_segments} segmentos recebidos", end="")

        except socket.timeout:
          print("\n Burst finalizado ou pacotes perdidos. Checando por segmentos faltantes...")
          break
      
      # Verifica se todos os pacotes foram recebidos
      if received_count == total_segments:
        print("\nTodos os segmentos foram recebidos! Verificando a integridade do arquivo...")
        break

      # Identifica os segmentos faltantes e envia um NACK
      missing_seqs = [str(i) for i, chunk in enumerate(received_chunks) if chunk is None]
      if missing_seqs:
        print(f"Número de segmentos faltantes: {len(missing_seqs)} Solicitando em lotes...")

        for i in range(0, len(missing_seqs), NACK_BATCH_SIZE):
          batch = missing_seqs[i:i + NACK_BATCH_SIZE]
          nack_payload = ",".join(batch).encode()
          nack_header = create_header(0, 0, b'\x00'*16, NACK)
          
          print(f"   -> Solicitando lote de {len(batch)} segmentos começando por {batch[0]}")
          sock.sendto(nack_header + nack_payload, server_address)
        
        print("Todos os Nacks foram enviados para o servidor.")
    
    # Monta o arquivo
    full_data = b"".join(received_chunks)
    
    # Verifica novamente a integridade e escreve o resultado
    if calculate_md5(full_data) == full_file_md5:
      output_filename = f"received_{filename}"
      with open(output_filename, 'wb') as f:
        f.write(full_data)
      print(f"Transferência do arquivo realizada com succeso! Salvo como '{output_filename}'.")
      
      # Envia o ACK final para o servidor
      ack_header = create_header(0, 0, b'\x00'*16, ACK)
      sock.sendto(ack_header, server_address)
      print("ACK final enviado.")
    else:
      print("Verificação do arquivo falhou! Hashes MD5 não batem.")

if __name__ == "__main__":
    main()