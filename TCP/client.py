import socket
import threading
import protocol
import os

# Configurações do cliente
HOST = "127.0.0.1"
PORT = 12345
DOWNLOAD_DIR = 'client_downloads'  # Pasta para salvar arquivos baixados

#------------------------------------------------------------------------------

def listen_for_messages(sock, stop_event):
    """
    Thread responsável por receber arquivos e mensagens do chat do servidor.
    """
    while not stop_event.is_set():
        try:
            # Aguarda e recebe mensagem do servidor
            response = protocol.receive_json(sock)
            if not response:
                print("\n[DISCONNECTED] Server closed connection.")
                stop_event.set()
                break

            msg_type = response.get('type')

            # Mensagem de chat recebida
            if msg_type == 'CHAT':
                sender = response.get('sender', 'Unknown')
                message = response.get('message')
                print(f"\n>> [{sender}]: {message}")
                print("Enter command: ", end='', flush=True)

            # Metadados de arquivo recebido
            elif msg_type == 'FILE_META':
                status = response.get('status')
                if status == 'ERROR':
                    print(f"\n[SERVER ERROR] {response.get('message')}")
                else:
                    # Recebe os bytes do arquivo enviado pelo servidor
                    filename = response.get('filename')
                    filesize = response.get('filesize')
                    server_hash = response.get('sha256')
                    
                    print(f"\n[DOWNLOADING] Receiving {filename} ({filesize/1024/1024:.2f} MB)...")
                    
                    save_path = os.path.join(DOWNLOAD_DIR, filename)
                    protocol.receive_file_content(sock, save_path, filesize)
                    
                    # Verifica integridade do arquivo baixado
                    print("[VERIFYING] Calculating SHA-256...")
                    local_hash = protocol.calculate_file_hash(save_path)
                    
                    if local_hash == server_hash:
                        print(f"[SUCCESS] File saved to {save_path}. Integrity Verified.")
                    else:
                        print(f"[WARNING] File corrupted! Hashes do not match.")
                
                print("Enter command: ", end='', flush=True)

        except Exception as e:
            # Trata erro de conexão
            if not stop_event.is_set():
                print(f"\n[!] Connection Error: {e}")
            stop_event.set()
            break

#------------------------------------------------------------------------------

def main():
    """
    Inicializa o cliente, conecta ao servidor e gerencia comandos do usuário.
    """

    # Cria pasta de downloads se não existir
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"Created directory '{DOWNLOAD_DIR}' to store downloaded files.")


    # Solicita IP e porta do servidor ao usuário
    ip = input("Enter Server IP (default localhost): ") or '127.0.0.1'
    port = input("Enter Server Port (default 12345): ") or '12345'

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
        try:
            # Tenta conectar ao servidor
            c.connect((HOST, PORT))
            print(f"Connected to {ip}:{port}")
        except Exception as e:
            print(f"Could not connect: {e}")
            return
        
        stop_event = threading.Event()

        # Inicia thread para escutar mensagens do servidor
        listener = threading.Thread(target=listen_for_messages, args=(c, stop_event), daemon=True)
        listener.start()

        # Exibe comandos disponíveis ao usuário
        print("\n--- COMMANDS ---")
        print("1. Chat [message]")
        print("2. File [filename]")
        print("3. Log Out")
        print("----------------")

        while not stop_event.is_set():
            try:
                # Lê comando do usuário
                user_input = input("Enter command: ")
                parts = user_input.split(" ", 1)
                cmd = parts[0].lower()

                # Comando para sair
                if cmd == "log" or cmd == "logout" or cmd == "exit":
                    protocol.send_json(c, {"type": "EXIT"})
                    stop_event.set()
                    break

                # Comando de chat
                elif cmd == "chat":
                    if len(parts) < 2:
                        print("Usage: Chat [message]")
                        continue
                    msg = parts[1]
                    protocol.send_json(c, {"type": "CHAT", "message": msg})

                # Comando para solicitar arquivo
                elif cmd == "file":
                    if len(parts) < 2:
                        print("Usage: File [filename.ext]")
                        continue
                    filename = parts[1]
                    protocol.send_json(c, {"type": "FILE_REQ", "filename": filename})

                else:
                    print("Unknown command.")

            except KeyboardInterrupt:
                protocol.send_json(c, {"type": "EXIT"})
                break
            except Exception as e:
                print(f"Error sending data: {e}")
                break

        c.close()
        print("Client application closed.")

#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
