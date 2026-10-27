##
# atmoswing/atmoswing-vigicrues

# Steps ordered from the less frequently changed to the more frequently
# changed to ensure the build cache is reused.

# AtmoSwing Forecaster v3.1.0 (Ubuntu 26.04), épinglée par digest pour des
# builds reproductibles. Mise à jour du digest : Dependabot (.github/dependabot.yml).
FROM atmoswing/forecaster:v3.1.0@sha256:1d075cbc5e7a008c164070184cdb5e17aa9b2099a7f3039294f48e4d3b8ba71d

WORKDIR /app

# System dependencies (openssh-client fournit ssh-keyscan pour l'option known_hosts)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libeccodes0 \
        netcdf-bin \
        openssh-client \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Le Python du système est géré par apt (PEP 668) : le module est installé dans un
# environnement virtuel, placé en tête du PATH.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
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
