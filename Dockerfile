FROM python:3.9.13
ARG GOOGLE_DRIVE_AUTH=""
ARG DEBUG_MODE=0

RUN apt-get update
RUN apt-get install -y default-jre
RUN apt-get --no-install-recommends install libreoffice -y


RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app

CMD python app.py
