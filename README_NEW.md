# CUIDA+Care Worker - GCP Native Architecture

Sistema de processamento de mensagens serverless com rastreamento completo de jobs usando Cloud Run + Pub/Sub + Cloud SQL PostgreSQL.

## 📋 Arquitetura Implementada

### Componentes

1. **Cloud Run** (`temporal-worker`)
   - Worker HTTP Flask para processar mensagens Pub/Sub
   - Health checks: `/health` e `/readiness`
   - Logging estruturado JSON com Cloud Logging
   - Rastreamento completo de jobs em PostgreSQL

2. **Pub/Sub**
   - **Topic principal**: `hello-topic`
   - **Subscription**: `hello-sub` (push para Cloud Run)
   - **Dead Letter Queue**: `hello-topic-dlq` (após 5 tentativas falhadas)
   - **DLQ Subscription**: `hello-sub-dlq`

3. **Cloud SQL PostgreSQL 15**
   - **Instância**: `cuida-care-db` (IP: 136.116.107.199)
   - **Database**: `cuida_care`
   - **Usuário**: `app_user`
   - **Connection**: Cloud SQL Connector (sem IP público necessário)

4. **GitHub Actions CI/CD**
   - Build automático com Cloud Build
   - Deploy automático para Cloud Run
   - Workflow: `.github/workflows/cloud-run-deploy.yml`

### Tabelas do Banco de Dados

#### `jobs`
Rastreamento de execução de jobs com campos:
- `job_id`, `message_id`, `status`, `payload`, `result`, `error_message`
- `retry_count` / `max_retries`, timestamps, `correlation_id`

#### `event_logs`  
Auditoria completa com `event_type`, `job_id`, `data`, `metadata`

#### `system_metrics`
Métricas de sistema com `metric_name`, `metric_value`, `labels`

## 🚀 Deploy (Próximo Deploy)

### 1. Configurar Variáveis de Ambiente

```powershell
gcloud run services update temporal-worker `
  --update-env-vars "CLOUD_SQL_CONNECTION_NAME=adc-agent:us-central1:cuida-care-db,DB_NAME=cuida_care,DB_USER=app_user,DB_PASSWORD=CuidaCare2025!Secure,LOG_LEVEL=INFO,ENABLE_CLOUD_LOGGING=true" `
  --add-cloudsql-instances adc-agent:us-central1:cuida-care-db `
  --region=us-central1 `
  --project=adc-agent
```

### 2. Deploy via GitHub Actions

```powershell
git add .
git commit -m "feat: add database tracking and structured logging"
git push origin main
```

### 3. Testar Sistema

```powershell
# Health check
curl https://temporal-worker-zpok2l5u7q-uc.a.run.app/health

# Readiness check (database)
curl https://temporal-worker-zpok2l5u7q-uc.a.run.app/readiness

# Publicar mensagem
gcloud pubsub topics publish hello-topic --message="Test with DB tracking" --project=adc-agent
```

## 🔍 Monitoramento

### Consultas SQL Úteis

```sql
-- Jobs recentes
SELECT job_id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;

-- Taxa de sucesso (24h)
SELECT status, COUNT(*), ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(),2) 
FROM jobs WHERE created_at > NOW()-INTERVAL '24h' GROUP BY status;

-- Tempo médio de processamento
SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) 
FROM jobs WHERE status='completed' AND created_at > NOW()-INTERVAL '1h';
```

## 📊 Status & Próximos Passos

**✅ Sprint 1 Completo - Fundação Robusta**
- Cloud SQL PostgreSQL 15
- Structured Logging (JSON + Cloud Logging)
- Dead Letter Queue
- Health Checks
- Database Schema

**🔄 Sprint 2 - Escalabilidade (Próximo)**
- Cloud Memorystore (Redis) cache
- FastAPI REST API
- Grafana dashboards

**📅 Sprint 3 - Segurança & IaC**
- Terraform completo
- Workload Identity
- Cloud Armor + VPC

---

**Última atualização**: 19 de Novembro de 2025
