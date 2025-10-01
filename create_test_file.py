import os

FILE_NAME = "20mb.bin"
FILE_SIZE_MB = 20
CHUNK_CONTENT = b"Este e um pedaco de amostra para o arquivo binario usado para testes de transferencia UDP. 1234567890\n"

file_size_bytes = int(FILE_SIZE_MB * 1024 * 1024)
chunk_size = len(CHUNK_CONTENT)
num_chunks = file_size_bytes // chunk_size

try:
    with open(FILE_NAME, "wb") as f:
        for _ in range(num_chunks + 1):
            f.write(CHUNK_CONTENT)
    
    with open(FILE_NAME, "ab") as f:
        f.truncate(file_size_bytes)
        
    print(f"Arquivo criado com sucesso '{FILE_NAME}'")
    print(f"Tamanho do arquivo: {os.path.getsize(FILE_NAME) / (1024*1024):.2f} MB")

except IOError as e:
  print(f"Erro criando o arquivo: {e}")