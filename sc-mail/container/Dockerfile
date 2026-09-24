FROM public.ecr.aws/docker/library/python:3.12-slim
RUN pip install --no-cache-dir boto3
WORKDIR /app
COPY app.py /app/app.py
EXPOSE 8080
CMD ["python","/app/app.py"]
