import socket
import threading
import protocol
import os

HOST = "0.0.0.0"
PORT = 12345
BUFFER_SIZE = 1024
FILES_DIR = "server_files"

clients = []
clients_lock = threading.Lock()

#------------------------------------------------------------------------------
def handle_client(conn: socket.socket, addr):
    print(f"[+] Connected: {addr}")

    with clients_lock:
        clients.append(conn)

    connected = True
    try:
        while connected:
            request = protocol.receive_json(conn)
            if not request:
                break

            cmd = request.get('type')

            if cmd == 'EXIT':
                print(f"[DISCONNECT] Client {addr} requested exit.")
                connected = False
            
            elif cmd == 'CHAT':
                msg = request.get('message')
                print(f"[CHAT from {addr}]: {msg}")

            elif cmd == 'FILE_REQ':
                filename = request.get('filename')
                filepath = os.path.join(FILES_DIR, filename)

                print(f"[FILE_REQ] Client {addr} requested {filename}")

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
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"Created directory '{FILES_DIR}'. Place files here to download.")

    print(f"Starting server on {HOST}:{PORT} ... (Ctrl-C to stop)")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[LISTENING] Server listening on {HOST}:{PORT}")

        threading.Thread(target=server_console_thread, daemon=True).start()
        try:
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 2}")
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            return

#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
