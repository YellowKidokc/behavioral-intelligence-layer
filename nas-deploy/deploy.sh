#!/bin/bash
# PIL NAS Brain Drive Deploy Script
# Run this ON the Synology NAS (SSH or Task Scheduler)
# Usage: bash /volume1/brain/deploy/deploy.sh

set -e
BRAIN="/volume1/brain"
DEPLOY="$BRAIN/deploy"

echo "=== PIL Brain Drive Deploy ==="
echo "$(date)"

# 1. Create directory structure (if not already done via SMB)
echo "[1/5] Ensuring directory structure..."
for dir in models captures understood embeddings ratings knowledge memory digests logs github deploy; do
  mkdir -p "$BRAIN/$dir"
done
echo "  Done."

# 2. Check Ollama
echo "[2/5] Checking Ollama..."
if curl -s --connect-timeout 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "  Ollama running on :11434"
  # Check for moondream
  if curl -s http://localhost:11434/api/tags | grep -q "moondream"; then
    echo "  moondream: installed"
  else
    echo "  Pulling moondream..."
    ollama pull moondream
  fi
  # Check for llava
  if curl -s http://localhost:11434/api/tags | grep -q "llava"; then
    echo "  llava: installed"
  else
    echo "  Pulling llava..."
    ollama pull llava
  fi
else
  echo "  WARNING: Ollama not running on localhost:11434"
  echo "  Check: docker ps | grep ollama"
  echo "  Start: docker start <ollama-container>"
fi

# 3. Deploy Qdrant
echo "[3/5] Deploying Qdrant..."
if docker ps --format '{{.Names}}' | grep -q pil-qdrant; then
  echo "  pil-qdrant already running"
else
  docker rm -f pil-qdrant 2>/dev/null || true
  docker run -d --name pil-qdrant \
    -p 6333:6333 -p 6334:6334 \
    -v "$BRAIN/embeddings":/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant
  echo "  pil-qdrant started on :6333"
fi

# 4. Deploy Infinity (embeddings)
echo "[4/5] Deploying Infinity..."
if docker ps --format '{{.Names}}' | grep -q pil-infinity; then
  echo "  pil-infinity already running"
else
  docker rm -f pil-infinity 2>/dev/null || true
  docker run -d --name pil-infinity \
    -p 7997:7997 \
    -v "$BRAIN/models":/app/.cache \
    --restart unless-stopped \
    michaelf34/infinity:latest \
    v2 --model-name-or-path sentence-transformers/all-MiniLM-L6-v2 --port 7997
  echo "  pil-infinity started on :7997"
fi

# 5. Deploy PIL API
echo "[5/5] Deploying PIL API..."
if docker ps --format '{{.Names}}' | grep -q pil-api; then
  echo "  pil-api already running"
else
  docker rm -f pil-api 2>/dev/null || true
  cd "$DEPLOY"
  docker build -t pil-api:latest .
  docker run -d --name pil-api \
    -p 8420:8420 \
    -v "$BRAIN":/data \
    -e PIL_DATA_DIR=/data \
    -e OLLAMA_URL=http://host.docker.internal:11434 \
    --add-host host.docker.internal:host-gateway \
    --restart unless-stopped \
    pil-api:latest
  echo "  pil-api started on :8420"
fi

echo ""
echo "=== Deploy Complete ==="
echo "Services:"
echo "  PIL API:   http://192.168.1.177:8420/status"
echo "  Qdrant:    http://192.168.1.177:6333/dashboard"
echo "  Infinity:  http://192.168.1.177:7997"
echo ""
echo "Smoke test:"
echo "  curl http://localhost:8420/status"
echo "  curl http://localhost:6333/collections"
echo "  curl http://localhost:7997/health"
