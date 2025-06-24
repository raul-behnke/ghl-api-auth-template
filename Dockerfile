# Dockerfile
# Use uma imagem base Python oficial
FROM python:3.9-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o diretório src e o arquivo de armazenamento de tokens (se existir) para o contêiner
# Para produção, o token_storage.json não deve ser copiado diretamente,
# mas sim montado via volume ou gerenciador de segredos.
COPY src/ ./src/
# COPY token_storage.json . # Descomente para testes locais com persistência dentro do contêiner

# Define a variável de ambiente para que Python imprima logs imediatamente
ENV PYTHONUNBUFFERED 1

# Comando para executar a aplicação
CMD ["python", "src/auth_handler.py"]