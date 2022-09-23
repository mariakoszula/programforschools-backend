FROM python:3.9.13
ARG GOOGLE_DRIVE_AUTH=""
ARG DEBUG_MODE=0

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app

CMD python app.py
