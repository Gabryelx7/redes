import socket
import threading

HOST = "127.0.0.1"
PORT = 12345
ENC = "utf-8"
BUFFER_SIZE = 1024

def handle_client(conn: socket.socket, addr):
    print(f"[+] Connected: {addr}")
    with conn:
        try:
            greeting = "Hello, World! Welcome to the multithreaded server.\n"
            conn.sendall(greeting.encode(ENC))

            while True:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    print(f"[-] Connection closed by {addr}")
                    break
                text = data.decode(ENC).strip()
                print(f"[{addr}] -> {text}")
                if text.lower() in ("quit", "exit"):
                    conn.sendall("Goodbye!\n".encode(ENC))
                    break
                
                response = f"Server received: {text}\n"
                conn.sendall(response.encode(ENC))
        except Exception as e:
            print(f"[!] Error with {addr}: {e}")
    print(f"[.] Handler finished for {addr}")

def main():
    print(f"Starting server on {HOST}:{PORT} ... (Ctrl-C to stop)")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        try:
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("\nServer shutting down...")

if __name__ == "__main__":
    main()
