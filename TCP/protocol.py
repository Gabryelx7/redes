import socket
import struct
import json
import os
import hashlib

# Protocol Constants
HEADER_FORMAT = '!I'  # Network byte order (Big Endian), Unsigned Int
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
CHUNK_SIZE = 4096  # 4KB chunks for file transfer
ENC = "utf-8"

def send_json(sock, data_dict):
    """Encodes a dictionary as JSON and sends it with a length prefix."""
    json_data = json.dumps(data_dict).encode(ENC)
    length_packed = struct.pack(HEADER_FORMAT, len(json_data))
    sock.sendall(length_packed + json_data)

def receive_json(sock):
    """Reads a length prefix, then reads the JSON payload."""
    # Read the length header
    header_data = recv_all(sock, HEADER_SIZE)
    if not header_data:
        return None
    
    msg_length = struct.unpack(HEADER_FORMAT, header_data)[0]
    
    # Read the actual JSON data
    payload_data = recv_all(sock, msg_length)
    if not payload_data:
        return None
        
    return json.loads(payload_data.decode(ENC))

def recv_all(sock, n):
    """Helper to ensure we get exactly n bytes (handling TCP fragmentation)."""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def calculate_file_hash(filepath):
    """Calculates SHA-256 of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def send_file(sock, filepath):
    """Sends raw file bytes in chunks."""
    with open(filepath, 'rb') as f:
        while True:
            bytes_read = f.read(CHUNK_SIZE)
            if not bytes_read:
                break
            sock.sendall(bytes_read)

def receive_file_content(sock, filepath, filesize):
    """Receives raw file bytes and saves them."""
    received = 0
    with open(filepath, 'wb') as f:
        while received < filesize:
            # Determine how much to read (don't read past the file end)
            to_read = min(CHUNK_SIZE, filesize - received)
            chunk = recv_all(sock, to_read)
            if not chunk:
                raise Exception("Socket closed during file transfer")
            f.write(chunk)
            received += len(chunk)