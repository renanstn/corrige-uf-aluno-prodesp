FROM python:3

ADD . /app
WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

CMD python src/api.py
