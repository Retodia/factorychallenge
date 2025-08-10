# ===== .dockerignore =====
__pycache__/
*.pyc
*.pyo
*.pyd
.git/
.gitignore
README.md
.env
.pytest_cache/
.coverage
.venv/
venv/
*.log

# ===== .gitignore =====
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

credentials/
serviceAccountKey.json
*.log

# ===== __init__.py files =====
# Create empty __init__.py files in these directories:
# config/__init__.py
# services/__init__.py  
# handlers/__init__.py
# utils/__init__.py
# models/__init__.py

# ===== deploy.sh =====
#!/bin/bash

# Build and deploy to Cloud Run
echo "Building and deploying Challenge Factory..."

# Set your project ID
export PROJECT_ID="challengefactory-68021"
export SERVICE_NAME="challenge-factory"
export REGION="us-central1"

# Build image
echo "Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 10 \
  --max-instances 10

echo "Deployment completed!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"

# ===== README.md =====
# Challenge Factory - Retos Diarios

Sistema automatizado para generar retos diarios personalizados usando IA.

## Arquitectura
- **FastAPI**: API principal
- **Vertex AI**: Generación de texto (Gemini) e imágenes
- **Cloud TTS**: Generación de podcasts
- **Firestore**: Base de datos
- **Cloud Storage**: Almacenamiento de archivos
- **Cloud Scheduler**: Triggers diarios

## Deployment

1. Configurar proyecto GCP
2. Subir serviceAccountKey.json a credentials/
3. Ejecutar: `chmod +x deploy.sh && ./deploy.sh`

## Endpoints

- `POST /trigger-daily` - Cloud Scheduler
- `POST /firestore-webhook` - Firestore triggers  
- `GET /health` - Health check
- `GET /test/{user_id}` - Test user data

## Configuración

Editar archivos en `/prompts/` para personalizar:
- prompt1.txt
- prompt_retodia.txt  
- prompt_imagen.txt
- prompt_podcast.txt