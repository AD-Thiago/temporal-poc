param(
  [string]$PROJECT,
  [string]$REGION = "us-central1",
  [string]$SERVICE = "temporal-worker",
  [string]$IMAGE = $null,
  [string]$SECRET_NAME = "temporal-api-key",
  [string]$TEMPORAL_TARGET = "cloud.temporal.io:443",
  [string]$TEMPORAL_NAMESPACE = "default"
)

if (-not $PROJECT) {
  Write-Error "Argument --PROJECT is required"
  exit 1
}

if (-not $IMAGE) {
  $IMAGE = "gcr.io/$PROJECT/$SERVICE:latest"
}

gcloud config set project $PROJECT

Write-Host "Submitting Cloud Build to build and push image: $IMAGE"
gcloud builds submit --tag $IMAGE .

$secret = gcloud secrets list --filter="name:$SECRET_NAME" --format="value(name)" --project $PROJECT 2>$null
if (-not $secret) {
  Write-Host "Creating secret $SECRET_NAME"
  Write-Host "Por favor, crie manualmente o secret '$SECRET_NAME' no Secret Manager com sua API key, ou execute:"
  Write-Host "echo 'SUA_API_KEY' | gcloud secrets create $SECRET_NAME --data-file=- --project=$PROJECT"
}

Write-Host "Deploying to Cloud Run: $SERVICE in $REGION"
gcloud run deploy $SERVICE `
  --image $IMAGE `
  --region $REGION `
  --platform managed `
  --set-env-vars TEMPORAL_TARGET=$TEMPORAL_TARGET,TEMPORAL_NAMESPACE=$TEMPORAL_NAMESPACE `
  --update-secrets TEMPORAL_API_KEY=projects/$PROJECT/secrets/$SECRET_NAME:latest `
  --project $PROJECT

Write-Host "Deploy finished. Use 'gcloud run services describe $SERVICE --region $REGION --project $PROJECT' to inspect." 
