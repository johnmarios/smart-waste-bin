# get a lightweight Python image
FROM python:3.11-slim

# whatever print statements we have will be displayed immediately
ENV PYTHONUNBUFFERED=1

# set a working directory for the app inside the container
WORKDIR /app

# copy the requirements file inside the container and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the app's code inside the container in the /app directory
COPY pirlib/ pirlib/
COPY models/ models/
COPY producer.py consumer.py ./

# create a directory for the app where consumer can store data
RUN mkdir -p /data

# Default command; docker-compose overrides this per service
# so by default, the producer will run with simulation and verbose output, connecting to the broker service
CMD ["python", "producer.py", "--broker", "broker", "--simulate", "--verbose"]

