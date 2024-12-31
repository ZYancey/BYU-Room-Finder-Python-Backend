# Load environment variables from .env file
include .env
export $(shell sed 's/=.*//' .env)

# Read the version number from the VERSION file
VERSION := $(shell cat VERSION)
# Define the Python interpreter
PYTHON = ./venv/bin/python

# YEAR_TERM is set in the .env file and follows the following format
# YYYYT where YYYY is the year and T is the term (1 for Winter, 3 for Spring, 4 for Summer and 5 for Fall)
scrape-db:
	$(PYTHON) scripts/scrape.py

# Initialize the database by running the schema.sql script (WARNING: This will drop all relevant tables)
initialize-db:
	PGPASSWORD=$(DB_PASSWORD) psql -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME) -f templates/schema.sql

# Create the .env file with dummy data
create-env:
	echo "DB_HOST=postgresql" > .env
	echo "DB_PORT=5432" >> .env
	echo "DB_NAME=byu" >> .env
	echo "DB_USER=REPLACE_ME" >> .env
	echo "DB_PASSWORD=REPLACE_ME" >> .env
	echo "YEAR_TERM=20251" >> .env

# Build the Docker image
docker-build:
	docker build -t roomfinder:$(VERSION) .

# Deploy the Docker container
docker-deploy:
	docker stop RoomFinder || true
	docker rm RoomFinder || true
	docker run -d --name RoomFinder -p 8080:8080 roomfinder:$(VERSION)

# Build and deploy the Docker container
docker: docker-build docker-deploy