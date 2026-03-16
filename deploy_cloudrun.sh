#!/bin/bash
# =============================================================================
# DEPLOY SCRIPT — Google Cloud Run
# Afirma E-vias Management System
# =============================================================================
# Uso: bash deploy_cloudrun.sh [PROJECT_ID] [REGION]
# Exemplo: bash deploy_cloudrun.sh meu-projeto-gcp us-central1
# =============================================================================

set -e  # Para na primeira falha

# ── Configurações ─────────────────────────────────────────────────────────────
PROJECT_ID="${1:-SEU_PROJECT_ID}"
REGION="${2:-us-central1}"
SERVICE_NAME="afirma-evias"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo ""
echo "=================================================="
echo "  DEPLOY — Afirma E-vias → Google Cloud Run"
echo "=================================================="
echo "  Projeto  : ${PROJECT_ID}"
echo "  Região   : ${REGION}"
echo "  Serviço  : ${SERVICE_NAME}"
echo "  Imagem   : ${IMAGE_NAME}"
echo "=================================================="
echo ""

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo "ERRO: gcloud CLI não encontrado."
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Definir projeto ativo
echo ">> Configurando projeto GCP..."
gcloud config set project "${PROJECT_ID}"

# Habilitar APIs necessárias
echo ">> Habilitando APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    --project="${PROJECT_ID}"

# Build e push da imagem via Cloud Build
echo ">> Construindo imagem Docker..."
gcloud builds submit \
    --tag "${IMAGE_NAME}:latest" \
    --project="${PROJECT_ID}" \
    .

# Deploy no Cloud Run
echo ">> Fazendo deploy no Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}:latest" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --timeout 300 \
    --concurrency 80 \
    --port 8080 \
    --set-env-vars "PYTHONUNBUFFERED=1" \
    --project="${PROJECT_ID}"

# Obter URL do serviço
echo ""
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo "=================================================="
echo "  DEPLOY CONCLUIDO!"
echo "  URL: ${SERVICE_URL}"
echo "=================================================="
