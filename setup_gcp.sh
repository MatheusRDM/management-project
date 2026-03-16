#!/bin/bash
# =============================================================================
# SETUP COMPLETO — Google Cloud Run + Load Balancer + SSL + Domínio
# Afirma E-vias Management System
# Domínio: afirmaevias.com.br
#
# USO: bash setup_gcp.sh SEU_PROJECT_ID
# EXEMPLO: bash setup_gcp.sh afirma-evias-prod
#
# O que este script faz:
#  1. Ativa APIs necessárias no GCP
#  2. Build + Deploy inicial no Cloud Run
#  3. Cria Load Balancer com IP fixo
#  4. Provisiona certificado SSL gerenciado (HTTPS automático)
#  5. Mapeia domínio afirmaevias.com.br
#  6. Mostra os registros DNS a configurar no seu provedor
# =============================================================================

set -euo pipefail

# ── Configurações ─────────────────────────────────────────────────────────────
PROJECT_ID="${1:?ERRO: Informe o Project ID. Uso: bash setup_gcp.sh SEU_PROJECT_ID}"
REGION="us-central1"
SERVICE_NAME="afirma-evias"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
DOMAIN="afirmaevias.com.br"
WWW_DOMAIN="www.afirmaevias.com.br"
LB_NAME="afirma-evias-lb"
IP_NAME="afirma-evias-ip"
SSL_CERT_NAME="afirma-evias-ssl"
NEG_NAME="afirma-evias-neg"
BACKEND_NAME="afirma-evias-backend"
URL_MAP_NAME="afirma-evias-urlmap"
HTTP_PROXY_NAME="afirma-evias-http-proxy"
HTTPS_PROXY_NAME="afirma-evias-https-proxy"
FW_HTTP_NAME="afirma-evias-fw-http"
FW_HTTPS_NAME="afirma-evias-fw-https"

# ── Cores para output ─────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  AFIRMA E-VIAS — Setup Google Cloud (Produção)${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "  Projeto  : ${PROJECT_ID}"
echo -e "  Região   : ${REGION}"
echo -e "  Serviço  : ${SERVICE_NAME}"
echo -e "  Domínio  : ${DOMAIN}"
echo -e "${GREEN}============================================================${NC}"
echo ""

# ── Verificar pré-requisitos ──────────────────────────────────────────────────
command -v gcloud &>/dev/null || err "gcloud CLI não encontrado. Instale em: https://cloud.google.com/sdk"
command -v docker  &>/dev/null || err "Docker não encontrado. Instale em: https://docs.docker.com/get-docker"

# ── 1. Configurar projeto ─────────────────────────────────────────────────────
log "Configurando projeto GCP: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" --quiet

# ── 2. Habilitar APIs ─────────────────────────────────────────────────────────
log "Habilitando APIs necessárias..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    compute.googleapis.com \
    certificatemanager.googleapis.com \
    --project="${PROJECT_ID}" --quiet
ok "APIs habilitadas"

# ── 3. Permissão para Cloud Build fazer deploy ────────────────────────────────
log "Configurando permissões do Cloud Build..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CB_SA}" \
    --role="roles/run.admin" --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CB_SA}" \
    --role="roles/iam.serviceAccountUser" --quiet
ok "Permissões configuradas"

# ── 4. Build e push da imagem inicial ────────────────────────────────────────
log "Construindo imagem Docker..."
gcloud builds submit \
    --tag "${IMAGE}:latest" \
    --project="${PROJECT_ID}" \
    . 2>&1 | tail -5
ok "Imagem construída e publicada"

# ── 5. Deploy inicial no Cloud Run ───────────────────────────────────────────
log "Fazendo deploy no Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE}:latest" \
    --platform=managed \
    --region="${REGION}" \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=5 \
    --timeout=300 \
    --concurrency=80 \
    --port=8080 \
    --set-env-vars="PYTHONUNBUFFERED=1" \
    --quiet
ok "Deploy no Cloud Run concluído"

# URL interna do Cloud Run
CLOUDRUN_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" --format="value(status.url)")
log "URL Cloud Run: ${CLOUDRUN_URL}"

# ── 6. IP externo fixo (necessário para Load Balancer) ───────────────────────
log "Reservando IP externo fixo..."
if ! gcloud compute addresses describe "${IP_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute addresses create "${IP_NAME}" \
        --global \
        --ip-version=IPV4 \
        --quiet
fi
STATIC_IP=$(gcloud compute addresses describe "${IP_NAME}" --global --format="value(address)")
ok "IP fixo reservado: ${STATIC_IP}"

# ── 7. Serverless NEG (conecta Load Balancer → Cloud Run) ────────────────────
log "Criando Serverless NEG..."
if ! gcloud compute network-endpoint-groups describe "${NEG_NAME}" \
    --region="${REGION}" --quiet 2>/dev/null; then
    gcloud compute network-endpoint-groups create "${NEG_NAME}" \
        --region="${REGION}" \
        --network-endpoint-type=serverless \
        --cloud-run-service="${SERVICE_NAME}" \
        --quiet
fi
ok "NEG criado"

# ── 8. Backend Service ────────────────────────────────────────────────────────
log "Criando Backend Service..."
if ! gcloud compute backend-services describe "${BACKEND_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute backend-services create "${BACKEND_NAME}" \
        --global \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --protocol=HTTPS \
        --quiet

    gcloud compute backend-services add-backend "${BACKEND_NAME}" \
        --global \
        --network-endpoint-group="${NEG_NAME}" \
        --network-endpoint-group-region="${REGION}" \
        --quiet
fi
ok "Backend configurado"

# ── 9. Certificado SSL gerenciado ─────────────────────────────────────────────
log "Criando certificado SSL gerenciado (HTTPS automático)..."
if ! gcloud compute ssl-certificates describe "${SSL_CERT_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute ssl-certificates create "${SSL_CERT_NAME}" \
        --domains="${DOMAIN},${WWW_DOMAIN}" \
        --global \
        --quiet
fi
ok "Certificado SSL criado (será provisionado após DNS ser configurado)"

# ── 10. URL Map (roteamento HTTP → HTTPS redirect) ───────────────────────────
log "Configurando roteamento HTTPS..."
# URL map principal
if ! gcloud compute url-maps describe "${URL_MAP_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute url-maps create "${URL_MAP_NAME}" \
        --default-service="${BACKEND_NAME}" \
        --global \
        --quiet
fi

# URL map para redirect HTTP → HTTPS
HTTP_REDIRECT_MAP="${URL_MAP_NAME}-http-redirect"
if ! gcloud compute url-maps describe "${HTTP_REDIRECT_MAP}" --global --quiet 2>/dev/null; then
    gcloud compute url-maps import "${HTTP_REDIRECT_MAP}" \
        --global \
        --source=/dev/stdin \
        --quiet <<EOF
name: ${HTTP_REDIRECT_MAP}
defaultUrlRedirect:
  redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  httpsRedirect: true
EOF
fi

# ── 11. HTTPS Proxy ────────────────────────────────────────────────────────────
if ! gcloud compute target-https-proxies describe "${HTTPS_PROXY_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute target-https-proxies create "${HTTPS_PROXY_NAME}" \
        --url-map="${URL_MAP_NAME}" \
        --ssl-certificates="${SSL_CERT_NAME}" \
        --global \
        --quiet
fi

# HTTP Proxy (só para redirect → HTTPS)
if ! gcloud compute target-http-proxies describe "${HTTP_PROXY_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute target-http-proxies create "${HTTP_PROXY_NAME}" \
        --url-map="${HTTP_REDIRECT_MAP}" \
        --global \
        --quiet
fi
ok "Proxies HTTP/HTTPS configurados"

# ── 12. Forwarding Rules (vincula IP ao proxy) ────────────────────────────────
if ! gcloud compute forwarding-rules describe "${FW_HTTPS_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute forwarding-rules create "${FW_HTTPS_NAME}" \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --address="${IP_NAME}" \
        --global \
        --target-https-proxy="${HTTPS_PROXY_NAME}" \
        --ports=443 \
        --quiet
fi

if ! gcloud compute forwarding-rules describe "${FW_HTTP_NAME}" --global --quiet 2>/dev/null; then
    gcloud compute forwarding-rules create "${FW_HTTP_NAME}" \
        --load-balancing-scheme=EXTERNAL_MANAGED \
        --address="${IP_NAME}" \
        --global \
        --target-http-proxy="${HTTP_PROXY_NAME}" \
        --ports=80 \
        --quiet
fi
ok "Load Balancer configurado"

# ── 13. Resultado final ───────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  SETUP CONCLUÍDO!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}  AGORA CONFIGURE O DNS NO SEU PROVEDOR:${NC}"
echo ""
echo -e "  Tipo  | Nome              | Valor"
echo -e "  ------+-------------------+------------------"
echo -e "  A     | afirmaevias.com.br | ${STATIC_IP}"
echo -e "  A     | www               | ${STATIC_IP}"
echo ""
echo -e "${YELLOW}  APÓS CONFIGURAR O DNS (pode levar 10-60 min):${NC}"
echo -e "  • O certificado SSL será provisionado automaticamente"
echo -e "  • O site ficará acessível em: https://${DOMAIN}"
echo -e "  • HTTP redireciona para HTTPS automaticamente"
echo ""
echo -e "${BLUE}  CI/CD AUTOMÁTICO:${NC}"
echo -e "  Configure o trigger no Cloud Build conforme README_DEPLOY.md"
echo ""
echo -e "${GREEN}============================================================${NC}"
