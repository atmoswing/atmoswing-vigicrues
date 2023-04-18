##
# atmoswing/atmoswing-vigicrues

# Steps ordered from the less frequently changed to the more frequently
# changed to ensure the build cache is reused.

FROM atmoswing/forecaster:main

WORKDIR /app

# Install dependencies
RUN apt-get update \
    && apt-get install -y libeccodes0 netcdf-bin ca-certificates python3-pip ssh

# Copy source code
COPY ./ .

# Install Python dependencies
RUN pip install -r requirements.txt \
    && pip install -r requirements-optional.txt

# Install own module
RUN pip install -e .


ENTRYPOINT ["python3", "-m", "atmoswing_vigicrues"]
