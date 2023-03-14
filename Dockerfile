FROM python:3.11

WORKDIR /opt/app

COPY requirements.txt .
RUN pip install --requirement requirements.txt

ENV FLASK_APP=logserver_tabulator.wsgi:app
COPY . .

EXPOSE 5000

CMD \
    gunicorn --bind "0.0.0.0:${P_PORT:-5000}" ${FLASK_APP}
