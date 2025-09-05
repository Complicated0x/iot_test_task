FROM python:3.12-slim
WORKDIR /app
COPY . .
EXPOSE 9000
CMD ["python", "main.py"]