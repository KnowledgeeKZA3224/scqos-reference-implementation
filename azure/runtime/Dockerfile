FROM python:3.12-slim
WORKDIR /app
COPY azure/runtime/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn","azure.runtime.app:app","--host","0.0.0.0","--port","8080"]
