import os
import sys
import time

DESTINATION_FOLDER = '../server_files'
CHUNK_SIZE = 1024 * 1024

def generate_file(filename, size_in_mb):
    """
    Cria um arquivo com conteúdo aleatório do tamanho especificado (em MB).
    """
    # Garante que o diretório do servidor existe
    if not os.path.exists(DESTINATION_FOLDER):
        os.makedirs(DESTINATION_FOLDER)
        print(f"Created directory '{DESTINATION_FOLDER}'")

    filepath = os.path.join(DESTINATION_FOLDER, filename)
    total_bytes = size_in_mb * 1024 * 1024
    bytes_written = 0

    print(f"Generating '{filename}' ({size_in_mb} MB)...")
    start_time = time.time()

    # Geramos um bloco de dados aleatórios de 1 MB e reutilizamos.
    random_chunk = os.urandom(CHUNK_SIZE)

    try:
        with open(filepath, 'wb') as f:
            while bytes_written < total_bytes:
                # Calcula os bytes restantes para escrever
                remaining = total_bytes - bytes_written
                
                # Determina o tamanho da escrita (um bloco inteiro ou o restante)
                to_write = min(CHUNK_SIZE, remaining)
                
                # Se estiver no final e precisar de menos que o tamanho do bloco, faz um slice
                if to_write < CHUNK_SIZE:
                    f.write(random_chunk[:to_write])
                    bytes_written += to_write
                else:
                    f.write(random_chunk)
                    bytes_written += len(random_chunk)

                # Indicador de progresso
                percent = (bytes_written / total_bytes) * 100
                sys.stdout.write(f"\rProgresso: {percent:.1f}%")
                sys.stdout.flush()

        end_time = time.time()
        print(f"\n[SUCCESS] Created '{filepath}'")
        print(f"Time taken: {end_time - start_time:.2f} seconds")

    except IOError as e:
        print(f"\n[ERROR] The file could not be written: {e}")

if __name__ == "__main__":
    # Verifica argumentos de linha de comando
    if len(sys.argv) < 3:
        print("Usage: python generate_test_file.py <nome_do_arquivo> <tamanho_em_MB>")
        print("Example: python generate_test_file.py video_teste.mp4 50")
    else:
        fname = sys.argv[1]
        try:
            fsize = int(sys.argv[2])
            generate_file(fname, fsize)
        except ValueError:
            print("Error: The size must be an integer (in MB).")