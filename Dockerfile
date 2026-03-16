# =============================================================================
# Dockerfile — Afirma E-vias Management System
# Deploy: Google Cloud Run
# =============================================================================

FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema (necessárias para python-Levenshtein e folium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas requirements primeiro (aproveita cache do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo o projeto
COPY . .

# Criar diretório de cache se não existir
RUN mkdir -p cache_certificados

# Porta exposta pelo Cloud Run
EXPOSE 8080

# Comando de inicialização
# Cloud Run injeta $PORT automaticamente (default 8080)
CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false
