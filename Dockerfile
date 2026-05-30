FROM python:3.11-slim

WORKDIR /app

# Only ping is needed in the container. Fail2Ban is reached through its Unix socket.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

CMD ["python", "-m", "smotritel"]
