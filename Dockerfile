FROM python:3.10-slim

ENV PORT=7860
ENV EASYOCR_MODULE_PATH=/app/easyocr_models

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 ffmpeg wget && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.render.txt .
RUN pip install --no-cache-dir -r requirements.render.txt

RUN python -c "import numpy; print('numpy:', numpy.__version__)"
RUN python -c "import cv2; print('cv2:', cv2.__version__)"

COPY . .
RUN rm -rf .venv venv
RUN mkdir -p static/screenshots static/challans videos models easyocr_models

CMD gunicorn app:app --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 4 --timeout 300