FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY *.py .
COPY important.txt .

# Mount the arxiv snapshot and commit output at runtime:
#   docker run -v /path/to/arxiv.json:/app/arxiv-metadata-oai-snapshot.json \
#              -v $(pwd)/commit:/app/commit \
#              -v ~/.gitconfig:/root/.gitconfig:ro \
#              daily-papers

ENV OLLAMA_BASE_URL=http://host.docker.internal:11434

CMD ["python", "main.py"]
