FROM python:3.10-alpine3.17

COPY requirements.txt /tmp/requirements.txt
COPY orders /orders

WORKDIR /orders

EXPOSE 8000

RUN apk add postgresql-client build-base postgresql-dev

RUN pip install -r /tmp/requirements.txt
RUN adduser --disabled-password user2
USER user2
