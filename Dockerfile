# Imagem única, usada tanto para a API (governance_copilot) quanto para o
# Dashboard (Streamlit) — o docker-compose.yml define o comando de cada
# serviço; o build é o mesmo (mesmas dependências para os dois).
FROM python:3.10-slim

WORKDIR /app

# Instala dependências primeiro (cache de camada Docker — só reinstala se
# os requirements mudarem, não a cada mudança de código).
COPY requirements-core.txt requirements-heavy.txt ./
RUN pip install --no-cache-dir -r requirements-core.txt -r requirements-heavy.txt

COPY . .

# Sem CMD default: docker-compose.yml define `command:` por serviço
# (uvicorn para a API, streamlit para o dashboard) — ver docker-compose.yml.
