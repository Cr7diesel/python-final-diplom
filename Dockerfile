FROM python:3.10-alpine3.17

WORKDIR /app

COPY . /app
COPY requirements.txt /tmp/requirements.txt

EXPOSE 8000

RUN apk add postgresql-client build-base postgresql-dev
RUN pip install -r /tmp/requirements.txt
RUN adduser --disabled-password user1
USER user1


