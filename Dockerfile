FROM python:3.10

COPY requirements.txt /src/requirements.txt
COPY . /src

WORKDIR /src

EXPOSE 8000

RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt