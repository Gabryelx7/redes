import socket
import struct
import hashlib
import re

BUFFER_SIZE = 2048
NACK_BATCH_SIZE = 150
MAX_NACK_ATTEMPS = 5

# --- Tipos de mensagens de protocolo ---
REQ = 0
DATA = 1
NACK = 2
INFO = 3
ERR = 4
ACK = 5
BUSY = 6

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

    # Recebe o endereço do servidor
    while True:
        address_input = input("Digite o endereço do servidor (@IP:Port): ")
        match = re.match(r"@([\d\.]+):(\d+)", address_input)
        if match:
            server_ip, server_port = match.group(1), int(match.group(2))
            break
        print("Formato invalido. Por favor use este formato: '@IP:Port'.")
    server_address = (server_ip, server_port)

    while True:
        # Recebe nome do arquivo
        filename = input("Digite o nome do arquivo para baixar: ")

        # Recebe simulação de perdas de pacotes
        loss_input = input(
            "Digite os números de sequências a serem descartados (e.g., 5,8,12 ou 'none'): ")
        packets_to_drop = set()
        if loss_input.lower() != 'none':
            try:
                packets_to_drop = {int(x.strip())
                                   for x in loss_input.split(',')}
            except ValueError:
                print("Entrada inválida. Nenhum pacote será perdido.")

        # Faz a solicitação do arquivo com header
        request_payload = f"GET /{filename}".encode()
        request_header = create_header(0, 0, b'\x00'*16, REQ)
        sock.sendto(request_header + request_payload, server_address)
        print(f"\nSolicitando arquivo '{filename}' de {server_address}...")

        # Espera o pacote de informações
        while True:
            try:
                sock.settimeout(20.0)
                info_packet, _ = sock.recvfrom(BUFFER_SIZE)
                _, total_segments, _, msg_type = unpack_header(info_packet)

                if msg_type != INFO:
                    if msg_type == ERR:
                        error_msg = info_packet[HEADER_SIZE:].decode()
                        print(f"Erro do servidor: {error_msg}")
                    elif msg_type == BUSY:
                        print("Esperando liberar servidor...")
                        continue
                    else:
                        print(
                            f"Erro no tipo de pacote recebido: {msg_type}. Abortando.")
                    break

                full_file_md5 = info_packet[HEADER_SIZE:]
                print(f"Pacote de informação recebido:")
                print(f"- Número esperado de segmentos: {total_segments}")
                print(f"- Hash MD5 do arquivo: {full_file_md5.hex()}")
                break

            except socket.timeout:
                print("Servidor não respondeu à tempo")
                break
        else:
            continue

        # Prepara para a recepção de pacotes
        received_chunks = [None] * total_segments
        received_count = 0
        nack_attemps = 0

        while received_count < total_segments:
            print("\n--- Iniciando a recepção ---")

            # Guarda o progresso
            last_received_count = received_count

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

                        print(
                            f"\r{received_count}/{total_segments} segmentos recebidos", end="")

                except socket.timeout:
                    print("\nBurst finalizado. Checando por segmentos faltantes...")
                    break

            # Verifica se todos os pacotes foram recebidos
            if received_count == total_segments:
                print(
                    "\nTodos os segmentos foram recebidos! Verificando a integridade do arquivo...")
                break

            # Identifica os segmentos faltantes e envia um NACK
            missing_seqs = [str(i) for i, chunk in enumerate(
                received_chunks) if chunk is None]
            if missing_seqs:
                # Verifica se algum progresso foi feito desde o último NACK
                if received_count == last_received_count:
                    nack_attemps += 1
                    print(
                        f"Nenhum pacote novo recebido. Tentantiva número {nack_attemps}")
                else:
                    nack_attemps = 0

                # Verifica se já fizemos o máximo de NACKS
                if nack_attemps >= MAX_NACK_ATTEMPS:
                    print('Servidor não está respondendo. Abortando transferência')
                    break

                print(
                    f"Número de segmentos faltantes: {len(missing_seqs)}. Solicitando em lotes...")

                for i in range(0, len(missing_seqs), NACK_BATCH_SIZE):
                    batch = missing_seqs[i:i + NACK_BATCH_SIZE]
                    nack_payload = ",".join(batch).encode()
                    nack_header = create_header(0, 0, b'\x00'*16, NACK)

                    print(
                        f"-- Solicitando lote de {len(batch)} segmentos começando por {batch[0]}")
                    sock.sendto(nack_header + nack_payload, server_address)

                print("Todos os Nacks foram enviados para o servidor.")

        # Monta o arquivo
        full_data = b"".join(received_chunks)

        # Verifica novamente a integridade e escreve o resultado
        if calculate_md5(full_data) == full_file_md5:
            output_filename = f"received_{filename}"
            with open(output_filename, 'wb') as f:
                f.write(full_data)
            print(
                f"Transferência do arquivo realizada com succeso! Salvo como '{output_filename}'.")

            # Envia o ACK final para o servidor
            ack_header = create_header(0, 0, b'\x00'*16, ACK)
            sock.sendto(ack_header, server_address)
            print("ACK final enviado.")
        else:
            print("Verificação do arquivo falhou! Hashes MD5 não batem.")

        # Prompt para nova transferência
        again = input("Deseja baixar outro arquivo? (s/n): ").strip().lower()
        if again != 's':
            print("Encerrando cliente.")
            break


if __name__ == "__main__":
    main()
