FROM python:3.10-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

# Install necessary build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade psycopg2-binary
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./scripts/server.py /code/
COPY ./scripts/search.py /code/
COPY ./scripts/models.py /code/
COPY ./.env /code/

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]