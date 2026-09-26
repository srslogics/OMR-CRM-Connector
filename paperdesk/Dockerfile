FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python setup_ocr.py
RUN useradd --create-home paperdesk && mkdir -p /var/lib/paperdesk && chown paperdesk /var/lib/paperdesk
USER paperdesk
ENV PAPERDESK_DATA=/var/lib/paperdesk
ENV COOKIE_SECURE=1
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
