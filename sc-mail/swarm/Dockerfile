FROM python:3.12-slim
WORKDIR /app
COPY sc-mail/swarm/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shadow_clone /app/shadow_clone
COPY supreme_mind/v1/supreme_mind_manifest.json /app/supreme_mind/v1/supreme_mind_manifest.json
COPY sc-mail/swarm/activate.py /app/sc-mail/swarm/activate.py
ENV PYTHONPATH=/app
CMD ["python","/app/sc-mail/swarm/activate.py"]
