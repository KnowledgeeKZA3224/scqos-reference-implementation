FROM python:3.12-slim
WORKDIR /lab
COPY . /lab
RUN python -m pip install --no-cache-dir -e '.[dev]'
CMD ["python", "-m", "scqos_acs_lab.harness", "--direct-local", "--output", "run-evidence/container.json"]
