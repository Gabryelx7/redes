import socket
import threading
import os

# Configurações do servidor
HOST = "0.0.0.0"
PORT = 8080
FILES_DIR = "../server_files" # Pasta onde ficam o index.html e as imagens

#------------------------------------------------------------------------------
def build_http_response(status_code, content_type, content):
    """
    Constrói o cabeçalho HTTP e anexa o conteúdo binário.
    Exemplo de Header:
    HTTP/1.0 200 OK
    Content-Type: text/html
    Content-Length: 500
    (linha em branco)
    (conteúdo)
    """
    if status_code == 200:
        status_line = "HTTP/1.0 200 OK"
    elif status_code == 404:
        status_line = "HTTP/1.0 404 Not Found"
    else:
        status_line = "HTTP/1.0 500 Internal Server Error"

    # Cabeçalhos
    header = f"{status_line}\r\n"
    header += f"Content-Type: {content_type}\r\n"
    header += f"Content-Length: {len(content)}\r\n"
    header += "Connection: close\r\n" # Encerra conexão após enviar
    header += "\r\n" # Linha em branco obrigatória entre Header e Body

    # Retorna cabeçalho codificado + conteúdo bruto
    return header.encode('utf-8') + content

#------------------------------------------------------------------------------

def get_content_type(filename):
    """Define o MIME type baseado na extensão do arquivo."""
    if filename.endswith(".html") or filename.endswith(".htm"):
        return "text/html"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        return "image/jpeg"
    elif filename.endswith(".png"):
        return "image/png"
    else:
        return "application/octet-stream"

#------------------------------------------------------------------------------

def handle_client(conn, addr):
    """
    Função que lida com a requisição HTTP de um único cliente (Browser).
    """
    # Exibe conexão estabelecida
    print(f"[+] Connected: {addr}")

    try:
        # Recebe a requisição
        request_data = conn.recv(1024).decode('utf-8')
        
        if not request_data:
            return

        # Pegar apenas a primeira linha (Ex: GET /imagem.jpg HTTP/1.1)
        request_line = request_data.split('\r\n')[0]
        print(f"[REQUEST] {addr} requested: {request_line}")

        # Parse simples da string
        parts = request_line.split()
        if len(parts) > 1:
            method = parts[0]  # GET
            path = parts[1]    # /index.html
            
            # Se a rota for apenas "/", define para index.html
            if path == "/":
                path = "/index.html"
            
            # Remove a barra inicial para usar no caminho do SO
            filename = path.lstrip("/")
            filepath = os.path.join(FILES_DIR, filename)

            # Verifica se arquivo existe e processa
            if os.path.exists(filepath) and os.path.isfile(filepath):
                # -- CASO 200 OK --
                with open(filepath, "rb") as f:
                    file_content = f.read()
                
                content_type = get_content_type(filename)
                response = build_http_response(200, content_type, file_content)
                conn.sendall(response)
                print(f"[SENT] 200 OK - {filename} ({len(file_content)} bytes)")
            
            else:
                # -- CASO 404 NOT FOUND --
                error_msg = "<h1>404 - Arquivo Nao Encontrado</h1><p>O servidor nao encontrou o recurso.</p>"
                response = build_http_response(404, "text/html", error_msg.encode('utf-8'))
                conn.sendall(response)
                print(f"[ERROR] 404 Not Found - {filename}")

    except Exception as e:
        print(f"[EXCEPTION] Error processing the client {addr}: {e}")
    
    finally:
        conn.close()
        # print(f"[END] Connection with {addr} ended.\n")

#------------------------------------------------------------------------------

def main():
    """
    Inicializa o servidor TCP Multithread.
    """
    # Cria diretório de arquivos se não existir
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"Created directory '{FILES_DIR}'. Place HTML/JPEG files here.")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))

    server_socket.listen(5)
    print(f"--- HTTP SERVER RUNNING ---")
    print(f"Access on the browser: http://localhost:{PORT}/index.html")
    print(f"Waiting for connections...\n")

    while True:
        # Aceita conexão
        conn, addr = server_socket.accept()
        
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    main()