FROM python:3.12-slim
WORKDIR /app
COPY sc-mail/azure/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY sc-mail/azure/app.py /app/app.py
COPY sc-mail/azure/sc_core.py /app/sc_core.py
COPY sc-mail/azure/manifest.xml /app/manifest.xml
COPY sc-mail/azure/taskpane.html /app/taskpane.html
EXPOSE 8080
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8080"]
