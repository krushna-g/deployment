
FROM python:3.11-alpine
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir  flask gunicorn


EXPOSE 5000
CMD gunicorn --bind 0.0.0.0:$PORT app:app

