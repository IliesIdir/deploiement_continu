# Image unique utilisée pour le script de traitement et pour le dashboard
FROM python:3.11-slim

# Tesseract pour l'OCR et la police DejaVu pour générer des images lisibles
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On copie d'abord les requirements pour profiter du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py run_pipeline.py scheduler.py generate_data.py dashboard.py ./
COPY pipeline/ pipeline/
COPY sql/ sql/

# Par défaut le conteneur lance le traitement en boucle
CMD ["python", "scheduler.py"]
