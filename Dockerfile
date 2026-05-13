FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY config.json .

ENV CONFIG_PATH=/app/config.json
ENV STATE_DB_PATH=/data/state.db

RUN mkdir -p /data

CMD ["python", "main.py"]
