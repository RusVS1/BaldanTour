FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.hf

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# GPU embeddings: install CUDA-enabled PyTorch + sentence-transformers.
# We install torch from the official PyTorch CUDA index.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch==2.6.0
RUN pip install --no-cache-dir sentence-transformers==3.4.1

# Prefetch the embedding model into the image so API requests don't download it at runtime.
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("prefetched")
PY

COPY . .

EXPOSE 8000

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
