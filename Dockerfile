# Dockerfile
# Use uma imagem base Python oficial
FROM python:3.9-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o diretório src para o contêiner
COPY src/ ./src/

# Define a variável de ambiente para que Python imprima logs imediatamente
ENV PYTHONUNBUFFERED 1

# Comando padrão para executar a aplicação
# O script agora tentará carregar o ghl_tokens.json de um volume montado
CMD ["python", "src/auth_handler.py"]