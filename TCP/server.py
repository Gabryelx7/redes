import socket
import threading
import protocol
import os


# Configurações do servidor
HOST = "0.0.0.0"
PORT = 12345       
FILES_DIR = "../server_files" # Pasta onde os arquivos ficam disponíveis para download


# Lista de clientes conectados e lock para acesso concorrente
clients = []
clients_lock = threading.Lock()

#------------------------------------------------------------------------------
def handle_client(conn: socket.socket, addr):
    """
    Função que lida com a comunicação de um cliente conectado.
    Recebe comandos, envia arquivos e mensagens conforme solicitado.
    """

    # Exibe conexão estabelecida
    print(f"[+] Connected: {addr}")

    # Adiciona cliente à lista protegida por lock
    with clients_lock:
        clients.append(conn)

    connected = True
    try:
        while connected:
            # Recebe requisição do cliente
            request = protocol.receive_json(conn)
            if not request:
                break

            cmd = request.get('type')

            # Cliente deseja desconectar
            if cmd == 'EXIT':
                print(f"[DISCONNECT] Client {addr} requested exit.")
                connected = False
            
            # Mensagem de chat recebida
            elif cmd == 'CHAT':
                msg = request.get('message')
                print(f"[CHAT from {addr}]: {msg}")

            # Cliente solicita arquivo
            elif cmd == 'FILE_REQ':
                filename = request.get('filename')
                filepath = os.path.join(FILES_DIR, filename)

                print(f"[FILE_REQ] Client {addr} requested {filename}")

                # Verifica se arquivo existe e envia metadados + conteúdo
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    filesize = os.path.getsize(filepath)
                    filehash = protocol.calculate_file_hash(filepath)
                    
                    protocol.send_json(conn, {
                        "type": "FILE_META",
                        "status": "OK",
                        "filename": filename,
                        "filesize": filesize,
                        "sha256": filehash
                    })
                    
                    protocol.send_file(conn, filepath)
                    print(f"[UPLOAD] Sent {filename} to {addr}")
                else:
                    # Arquivo não encontrado
                    protocol.send_json(conn, {
                        "type": "FILE_META",
                        "status": "ERROR",
                        "message": "File not found."
                    })
    except Exception as e:
        print(f"[!] Error with {addr}: {e}")
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()

#------------------------------------------------------------------------------

def server_console_thread():
    """
    Thread que permite ao servidor enviar mensagens de broadcast para todos os clientes conectados.
    """
    print("Server console active. Type a message to broadcast.")
    while True:
        msg = input()
        with clients_lock:
            for client_conn in clients:
                try:
                    protocol.send_json(client_conn, {
                        "type": "CHAT", 
                        "sender": "SERVER", 
                        "message": msg
                    })
                except:
                    pass

#------------------------------------------------------------------------------

def main():
    """
    Inicializa o servidor TCP, prepara diretório de arquivos e aceita conexões de clientes.
    """

    # Cria diretório de arquivos se não existir
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"Created directory '{FILES_DIR}'. Place files here to download.")

    # Cria socket TCP e inicia escuta
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[LISTENING] Server listening on {HOST}:{PORT}")

    # Inicia thread do console do servidor
    threading.Thread(target=server_console_thread, daemon=True).start()
    
    while True:
        # Aceita novas conexões de clientes
        conn, addr = s.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 2}")

#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
