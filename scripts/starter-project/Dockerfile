FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

COPY starter_project.py .

COPY ./datasets/ ./datasets/

CMD ["python", "starter_project.py"]
