# ===== deploy.sh (MEJORADO) =====
#!/bin/bash

# Challenge Factory Deployment Script
echo "🚀 Building and deploying Challenge Factory..."

# Configuration
export PROJECT_ID="challengefactory-68021"
export SERVICE_NAME="challenge-factory"
export REGION="us-central1"

# Verify gcloud is configured
echo "📋 Verifying Google Cloud configuration..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable texttospeech.googleapis.com

# Build image
echo "🔨 Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 10 \
  --max-instances 10 \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,REGION=$REGION"

echo "✅ Deployment completed!"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
echo "🌐 Service URL: $SERVICE_URL"

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s "$SERVICE_URL/health" || echo "❌ Health check failed"

echo ""
echo "🎯 Next steps:"
echo "1. Configure Cloud Scheduler to call: $SERVICE_URL/trigger-daily"
echo "2. Set up Firestore triggers to call: $SERVICE_URL/firestore-webhook"
echo "3. Test with: $SERVICE_URL/test/USER_ID"

# ===== cloud-scheduler-setup.sh =====
#!/bin/bash

# Setup Cloud Scheduler for daily triggers
echo "⏰ Setting up Cloud Scheduler..."

export PROJECT_ID="challengefactory-68021"
export SERVICE_NAME="challenge-factory"
export REGION="us-central1"
export SCHEDULER_REGION="us-central1"

# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")

# Create Cloud Scheduler job
gcloud scheduler jobs create http daily-challenges \
  --location=$SCHEDULER_REGION \
  --schedule="0 6 * * *" \
  --uri="$SERVICE_URL/trigger-daily" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"user_id": null}' \
  --time-zone="America/Mexico_City"

echo "✅ Cloud Scheduler configured!"
echo "📅 Daily challenges will run at 6:00 AM Mexico time"

# ===== setup-firestore-triggers.md =====
# FIRESTORE TRIGGERS SETUP

Para configurar los triggers de Firestore, necesitas crear Cloud Functions:

## 1. Crear Cloud Function para triggers

```bash
# Enable Cloud Functions API
gcloud services enable cloudfunctions.googleapis.com

# Deploy function (crear archivo separado)
gcloud functions deploy firestoreTrigger \
  --runtime python39 \
  --trigger-event providers/cloud.firestore/eventTypes/document.write \
  --trigger-resource projects/challengefactory-68021/databases/(default)/documents/retosdiarios/{documentId} \
  --source . \
  --entry-point firestore_trigger_handler
```

## 2. Código para Cloud Function (main.py):

```python
import requests
import json

def firestore_trigger_handler(data, context):
    """Triggered by Firestore document changes"""
    
    # Extract user_id and doc_id from the trigger
    document_path = context.resource
    doc_id = document_path.split('/')[-1]
    
    # Get the document data
    document = data.get('value', {})
    user_id = document.get('fields', {}).get('userid', {}).get('stringValue')
    
    if user_id and 'brief' in document.get('fields', {}):
        # Call Cloud Run webhook
        webhook_url = "https://challenge-factory-xxx.run.app/firestore-webhook"
        
        payload = {
            "user_id": user_id,
            "document_id": doc_id,
            "action": "update"
        }
        
        try:
            response = requests.post(webhook_url, json=payload)
            print(f"Webhook called successfully: {response.status_code}")
        except Exception as e:
            print(f"Error calling webhook: {str(e)}")
```

# ===== .env.example =====
# Example environment variables file
# Copy to .env and fill in your values

PROJECT_ID=challengefactory-68021
REGION=us-central1
FIRESTORE_DB=(default)

# Collections
COLLECTION_USERS=users
COLLECTION_INFOUSER=infouser
COLLECTION_AVANCES=avances
COLLECTION_RETOS=retosdiarios

# Storage
STORAGE_BUCKET=challengefactory-68021.firebasestorage.app
IMAGES_FOLDER=imagenes
PODCASTS_FOLDER=podcasts

# Vertex AI
VERTEX_AI_LOCATION=us-central1
GEMINI_MODEL=gemini-1.5-pro
IMAGEN_MODEL=imagegeneration@006

# TTS
TTS_VOICE_FEMALE=es-MX-Neural2-A
TTS_VOICE_MALE=es-MX-Neural2-B
TTS_LANGUAGE=es-MX

# Logging
LOG_LEVEL=INFO
MAX_CONCURRENT_USERS=10