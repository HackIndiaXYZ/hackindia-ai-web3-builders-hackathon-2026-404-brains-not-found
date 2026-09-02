FROM python:3.10-slim

ENV PORT=7860
ENV EASYOCR_MODULE_PATH=/app/easyocr_models

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 ffmpeg wget && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir torch==2.2.0+cpu torchvision==0.17.0+cpu --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import numpy; print('numpy:', numpy.__version__)"
RUN python -c "import cv2; print('cv2:', cv2.__version__)"

COPY . .
RUN rm -rf .venv venv
RUN mkdir -p static/screenshots static/challans videos models easyocr_models

RUN wget -q "https://huggingface.co/i-am-ankush/roadx-models/resolve/main/best.pt" -O models/best.pt && \
    wget -q "https://huggingface.co/i-am-ankush/roadx-models/resolve/main/Plate.pt" -O models/Plate.pt && \
    wget -q "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt" -O models/yolov8s.pt && \
    ls -lh models/

RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, model_storage_directory='/app/easyocr_models')" && \
    echo "EasyOCR models downloaded successfully"

CMD gunicorn app:app --bind 0.0.0.0:7860 --workers 1 --threads 4 --timeout 300