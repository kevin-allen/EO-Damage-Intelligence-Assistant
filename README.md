# EO Damage Intelligence Assistant

Local prototype that turns CV outputs from xView2 satellite imagery into
grounded disaster-assessment reports via RAG + a local LLM.

See [`software_requirements.md`](./software_requirements.md) and
[`software_architecture.md`](./software_architecture.md) for the full
design. Quick orientation:

- **CV** — ResNet50 fine-tuned offline on cropped xView2 patches; predictions
  are precomputed once per catalog scenario (no live inference at runtime).
- **RAG** — ChromaDB + sentence-transformers MiniLM over a curated
  `knowledge/` corpus.
- **LLM** — `qwen2.5:7b-instruct` via local Ollama. Generates prose only;
  numbers come from code-rendered markdown tables.
- **UI** — Streamlit at `http://localhost:8501` (loopback-bound, no auth).

## Layout

```
.
├── Dockerfile / docker-compose.yml / requirements.txt
├── scripts/                # offline jobs (training, precompute)
├── app/                    # streamlit app + cv / rag / llm / scenarios
├── knowledge/              # markdown docs for RAG (to be written)
└── predictions/            # gitignored; produced by precompute
```

## One-time setup

```sh
# 1. Extract xView2 tars under /data/xView2/

# 2. Build the image
docker compose build app

# 3. Train the classifier (~2-3 h on RTX 2080 Ti)
docker compose stop ollama
docker compose run --rm --gpus all app python scripts/train_classifier.py
docker compose start ollama

# 4. Precompute predictions for every scenario
docker compose stop ollama
docker compose run --rm --gpus all app python scripts/precompute_predictions.py
docker compose start ollama

# 5. Pull the LLM
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
```

## Run

```sh
docker compose up app
# open http://localhost:8501
```
