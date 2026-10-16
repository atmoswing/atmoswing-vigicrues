##
# atmoswing/atmoswing-vigicrues

# Steps ordered from the less frequently changed to the more frequently
# changed to ensure the build cache is reused.

# AtmoSwing Forecaster (branche main, Ubuntu 22.04), épinglée par digest pour des
# builds reproductibles. Mise à jour du digest : Dependabot (.github/dependabot.yml).
FROM atmoswing/forecaster:main@sha256:9428fbb9e262615fd352dfa0dfe0214536e4e65ad1e30e0b1d60ce869ec66063

WORKDIR /app

# System dependencies (openssh-client fournit ssh-keyscan pour l'option known_hosts)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libeccodes0 \
        netcdf-bin \
        openssh-client \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Le pip d'Ubuntu 22.04 (22.0) ignore la table [project] de pyproject.toml et
# installe un paquet vide nommé 'UNKNOWN' : une version récente est requise.
RUN python3 -m pip install --no-cache-dir --upgrade pip

# Python dependencies (layer reused as long as the requirements do not change)
COPY requirements.txt requirements-optional.txt ./
RUN python3 -m pip install --no-cache-dir \
        -r requirements.txt -r requirements-optional.txt

# Own module
COPY pyproject.toml README.md ./
COPY src ./src
RUN python3 -m pip install --no-cache-dir --no-deps . \
    && rm -rf build src/*.egg-info \
    && python3 -c "import atmoswing_vigicrues"

ENTRYPOINT ["python3", "-m", "atmoswing_vigicrues"]
