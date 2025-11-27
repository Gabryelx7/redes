import socket
import time

HOST = "127.0.0.1"
PORT = 12345
ENC = "utf-8"
BUFFER_SIZE = 1024

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        time.sleep(5)
        
        greeting = s.recv(BUFFER_SIZE).decode(ENC)
        print("Server:", greeting.strip())

        message = "Hello from client!"
        print("Client:", message)
        s.sendall((message + "\n").encode(ENC))
        reply = s.recv(BUFFER_SIZE).decode(ENC)
        print("Server:", reply.strip())

        s.sendall("quit\n".encode(ENC))
        final = s.recv(BUFFER_SIZE).decode(ENC)
        print("Server:", final.strip())

if __name__ == "__main__":
    main()
