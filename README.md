# Temporal POC

Este repositório contém um POC mínimo para executar workflows com o Temporal usando Python.

Pré-requisitos
- Docker (para rodar o servidor Temporal local)
- Python 3.10+

Passos rápidos (Windows PowerShell)

1. Subir o servidor Temporal localmente:

```powershell
cd "c:\\Users\\tcruz\\Desktop\\cmd care\\temporal-poc"
docker compose up -d
```

2. Instalar dependências Python (recomendo usar um virtualenv):

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

3. Rodar o worker (num terminal):

```powershell
python -m src.worker
```

4. Disparar o workflow cliente (outro terminal):

```powershell
python -m src.client
```

Comandos úteis
- Parar serviços Docker: `docker compose down`

Próximos passos
- Adicionar testes automatizados e CI
- Preparar infra como código (Terraform) para staging/produção

Mudança: este POC agora usa **Google Cloud Pub/Sub + Cloud Run** em vez de Temporal.

Rodando localmente (Publisher + Worker)

1. Defina variáveis de ambiente (exemplo):

```powershell
$env:GCP_PROJECT_ID = "YOUR_PROJECT_ID"
$env:PUBSUB_TOPIC = "hello-topic"
```

2. Para publicar uma mensagem localmente (usa credenciais ADC):

```powershell
python -m src.publisher
```

3. Para rodar o worker Flask localmente:

```powershell
# Ative o venv
.\.venv\Scripts\Activate.ps1
python -m src.worker_http
```

Deploy para Cloud Run (resumo de passos)

1. Autentique-se no GCP: `gcloud auth login` e `gcloud auth application-default login`.
2. Habilite APIs:

```powershell
gcloud services enable run.googleapis.com pubsub.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com --project=YOUR_PROJECT_ID
```

3. Faça build e push da imagem (Cloud Build):

```powershell
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/temporal-poc-worker:latest
```

4. Deploy no Cloud Run:

```powershell
gcloud run deploy temporal-worker --image gcr.io/YOUR_PROJECT_ID/temporal-poc-worker:latest --region us-central1 --platform managed --set-env-vars PUBSUB_TOPIC=hello-topic
```

5. Crie tópico Pub/Sub e uma subscription push apontando para a URL do Cloud Run (substitua SERVICE_URL):

```powershell
gcloud pubsub topics create hello-topic --project=YOUR_PROJECT_ID
gcloud pubsub subscriptions create hello-sub --topic=hello-topic --push-endpoint=SERVICE_URL/pubsub/push --ack-deadline=30 --project=YOUR_PROJECT_ID
```

Observação: para produção, prefira configurar autenticação entre Pub/Sub e Cloud Run usando um service account e verificação de token.

**Conectar ao Temporal Cloud (opcional)**

Se preferir não usar Docker local, você pode usar o Temporal Cloud (SaaS). Em alto nível:

1. Crie uma conta no Temporal Cloud e crie um `namespace` (nome do projeto/namespace).
2. Gere uma API key/credentials no painel do Temporal Cloud.
3. Exporte as variáveis de ambiente no PowerShell (exemplo):

```powershell
$env:TEMPORAL_TARGET = "cloud.temporal.io:443"
$env:TEMPORAL_NAMESPACE = "seu-namespace"
# Se o cloud exigir uma API key, exporte-a também (nome genérico):
$env:TEMPORAL_API_KEY = "sua-api-key-aqui"
```

4. Rode o `worker` e o `client` normalmente (eles lerão `TEMPORAL_TARGET` e `TEMPORAL_NAMESPACE`):

```powershell
python -m src.worker
python -m src.client
```

Observação: a autenticação exata para Temporal Cloud (header/token/mTLS) depende da configuração do serviço Cloud; após criar o namespace e a API key, siga as instruções do painel Temporal Cloud para obter o endpoint/credentials corretos. Se precisar, eu adapto o código para incluir headers de autorização ou certificado mTLS conforme o método de autenticação que você escolher.

---

**CI / CD (GitHub Actions)**

Este repositório inclui um workflow de exemplo para CI/CD que executa um build (via Cloud Build) e deploy para Cloud Run automaticamente quando houver push para a branch `main` (arquivo: `.github/workflows/cloud-run-deploy.yml`).

Passos rápidos para habilitar o CI/CD:

1. Crie um service account no projeto GCP (por exemplo `github-actions-sa`) e conceda as roles necessárias:
	- `roles/run.admin` (deploy no Cloud Run)
	- `roles/iam.serviceAccountUser` (para permitir deploy usando service account)
	- `roles/storage.admin` (para push em `gcr.io` via Cloud Build)
	- `roles/cloudbuild.builds.editor` (opcional, se usar Cloud Build)

2. Gere e baixe a chave JSON do service account e adicione-a como o secret `GCP_SA_KEY` no repositório GitHub (`Settings` → `Secrets` → `Actions`).

3. Garanta que a branch `main` (ou `master`) seja protegida conforme suas políticas e faça push para disparar o workflow.

Observação de segurança: mantenha a chave do service account com o mínimo de privilégios e rotacione a chave periodicamente. Para maior segurança, prefira usar Workload Identity Federation em vez de chaves long-lived.

---

**Removed: Temporal POC code**

O código do POC original com Temporal foi removido do repositório. Se você precisar do histórico completo, restaure a partir do controle de versão (git) ou peça para que eu recupere os arquivos arquivados antes da remoção.
No projeto atual, se `TEMPORAL_API_KEY` estiver definido, o `worker` e o `client` enviarão automaticamente um header `Authorization: Bearer <API_KEY>` ao conectar ao endpoint do Temporal. Se sua instância do Temporal Cloud usar outro método de autenticação (por exemplo mTLS), me avise que eu adapto o `Client.connect` para providenciar certificados TLS.
