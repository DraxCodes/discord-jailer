FROM --platform=$TARGETPLATFORM python:3.11-slim AS build

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . app

ENTRYPOINT ["python","-u","./app/jailer.py"]