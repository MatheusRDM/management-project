# Deploy — Afirma E-vias Management System
## Infraestrutura: Google Cloud Run + Load Balancer + SSL

---

## Arquitetura de Produção

```
GitHub (master)
      │  push
      ▼
Cloud Build  ──── build Docker ──── push GCR
      │
      └── deploy ──► Cloud Run (afirma-evias)
                          │
                    Serverless NEG
                          │
               HTTPS Load Balancer (IP fixo)
                          │
               Certificado SSL gerenciado
                          │
                  afirmaevias.com.br  ✅
```

**Fluxo HTTP → HTTPS:** Todo acesso HTTP (porta 80) redireciona automaticamente para HTTPS (porta 443).

---

## Pré-requisitos

1. **gcloud CLI** instalado: https://cloud.google.com/sdk/docs/install
2. **Docker** instalado: https://docs.docker.com/get-docker
3. **Projeto GCP** criado com billing ativo
4. **Domínio** `afirmaevias.com.br` com acesso ao painel DNS

---

## PASSO 1 — Setup único (executar uma vez)

```bash
# Autenticar no Google
gcloud auth login

# Executar setup completo (substitua pelo seu Project ID)
bash setup_gcp.sh SEU_PROJECT_ID
```

O script faz **tudo automaticamente**:
- Habilita APIs
- Build + Deploy no Cloud Run
- Cria IP fixo global
- Configura Load Balancer HTTPS
- Provisiona certificado SSL gerenciado
- Mostra os registros DNS a configurar

---

## PASSO 2 — Configurar DNS

Após o script terminar, adicione **2 registros A** no seu provedor de domínio:

| Tipo | Nome | Valor (IP do script) |
|------|------|----------------------|
| A | `afirmaevias.com.br` | `IP_EXIBIDO_PELO_SCRIPT` |
| A | `www.afirmaevias.com.br` | `IP_EXIBIDO_PELO_SCRIPT` |

> ⏳ Propagação DNS: 10 minutos a 1 hora
> ⏳ Certificado SSL: até 15 minutos após DNS propagado

---

## PASSO 3 — CI/CD Automático (GitHub → Cloud Run)

Configure o trigger no GCP para deploy automático a cada push:

1. Acesse **[console.cloud.google.com](https://console.cloud.google.com)**
2. Vá em **Cloud Build → Triggers → Criar trigger**
3. Configure:
   - **Nome**: `deploy-master`
   - **Evento**: Push para branch
   - **Branch**: `^master$`
   - **Repositório**: conectar GitHub → `MatheusRDM/management-project`
   - **Configuração**: `Cloud Build config file (YAML)` → `cloudbuild.yaml`
4. Clique em **Salvar**

✅ Pronto! A cada push em `master`, o pipeline executa automaticamente.

---

## Estrutura dos arquivos de infraestrutura

```
├── Dockerfile          # Imagem multi-stage, non-root, health check
├── .dockerignore       # Exclui .git, backups, secrets, pkl
├── cloudbuild.yaml     # Pipeline CI/CD: build → push → deploy
├── setup_gcp.sh        # Setup completo GCP (executar uma vez)
├── .streamlit/
│   └── config.toml     # Configurações Streamlit para produção
└── cloud_config.py     # Detecção cloud/local + fallback de dados
```

---

## Dados em produção

O app usa **cache estático em parquet** (sem depender do Google Drive):

| Arquivo | Conteúdo | Linhas |
|---------|----------|--------|
| `cache_certificados/db_novo_dashboard_067.parquet` | Dashboard Certificados | 2.052 |
| `cache_certificados/db_epr_form022a.parquet` | EPR Litoral Pioneiro | 704 |
| `cache_certificados/db_recebimentos.parquet` | Recebimentos | 416 |
| `cache_certificados/db_certificados_067.parquet` | Certificados 067 | 8.879 |
| `cache_certificados/cauq_projetos.parquet` | Projetos CAUQ | 386 |

Para **atualizar os dados** em produção:
1. Execute localmente com Google Drive conectado
2. Os caches são regenerados automaticamente
3. `git add cache_certificados/*.parquet && git commit && git push`
4. O CI/CD faz o deploy com os novos dados

---

## Credenciais de acesso (produção)

Usuários configurados no `auth.py` (fallback local):

| Usuário | Acesso |
|---------|--------|
| `Gestor` | Dashboard, Cronograma, CAUQ |
| `Geoloc` | Mapeamento CAUQ |
| `EPR` | EPR Litoral Pioneiro |
| `Dev` | Acesso completo |

Senha padrão: `Afirmaevias`

---

## Monitoramento

- **Logs**: GCP Console → Cloud Run → afirma-evias → Logs
- **Métricas**: GCP Console → Cloud Run → afirma-evias → Métricas
- **Uptime**: GCP Console → Cloud Monitoring → Uptime checks
