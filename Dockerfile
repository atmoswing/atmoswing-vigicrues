##
# terranum/voltoo:bullseye

# Steps ordered from the less frequently changed to the more frequently
# changed to ensure the build cache is reused.

FROM python:3.11

WORKDIR /app

# Install dependencies
RUN apt-get update \
    && apt-get install -y libeccodes netcdf-bin ca-certificates

# Copy source code
COPY ./ .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install own module
RUN pip install -e .


ENTRYPOINT ["python3", "/app/cli.py"]
