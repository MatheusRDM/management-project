# =============================================================================
# Dockerfile — Afirma E-vias Management System
# Build: multi-stage | Segurança: non-root user | Target: Google Cloud Run
# =============================================================================

# ── Stage 1: Builder (instala dependências) ───────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Dependências do sistema para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências em pasta isolada (wheel cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime (imagem final enxuta) ────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/app

WORKDIR /app

# Copiar apenas os pacotes instalados (sem build tools)
COPY --from=builder /install /usr/local

# Criar usuário não-root (segurança)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar código da aplicação
COPY --chown=appuser:appuser . .

# Garantir que o diretório de cache existe e tem permissão
RUN mkdir -p cache_certificados && chown -R appuser:appuser cache_certificados

# Usar usuário não-root
USER appuser

# Porta Cloud Run
EXPOSE 8080

# Health check (Cloud Run verifica este endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/_stcore/health')" || exit 1

# Entrypoint de produção
CMD ["sh", "-c", "streamlit run app.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false \
    --logger.level=warning"]
