#!/bin/bash
# ─── Redline Reveal — Cloud Run Deployment ─────────────────────────────────────
# Run this AFTER confirming with the user.
# Usage: bash deploy.sh

set -euo pipefail

PROJECT="redline-reveal"
REGION="us-central1"
SERVICE="redline-reveal"
IMAGE="gcr.io/${PROJECT}/${SERVICE}"

echo "🚀 Deploying Redline Reveal to Cloud Run..."
echo "   Project: ${PROJECT}"
echo "   Region:  ${REGION}"
echo "   Image:   ${IMAGE}"
echo ""

# 1. Build and push container image
echo "📦 Building Docker image..."
gcloud builds submit \
  --tag "${IMAGE}" \
  --project "${PROJECT}" \
  .

# 2. Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=0,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION}" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_MAPS_API_KEY=maps-api-key:latest"

echo ""
echo "✅ Deployment complete!"
echo "   URL: $(gcloud run services describe ${SERVICE} --region ${REGION} --project ${PROJECT} --format 'value(status.url)')"
