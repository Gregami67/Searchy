# Searchy

Semantic image search powered by CLIP — describe what you're looking for in natural language and find it in your local image collection.

## Description

Searchy uses OpenAI's CLIP model to embed images and text into a shared vector space, enabling fast semantic search over a local directory of images. On startup, all images are indexed via their visual embeddings and stored in Valkey. A watchdog watches for new or deleted images and keeps the index in sync automatically. Queries return visually similar results ranked by cosine distance.

**Features:**

- [x] Text-to-Image search
- [x] Valkey-Search with cosine similarity
- [x] Live directory watching with Watchdog
- [x] Flask API
- [x] Simple gallery frontend
- [x] Run with Docker Compose
- [x] Image-to-image search
- [ ] Text-to-video search
  - [ ] CLIP frame extraction
  - [ ] Whisper transcription extraction

## Getting Started

### Dependencies

- Python 3.12+
- Docker / Docker Compose
- pip

### Docker

```bash
# Copy default environment variables
cp .env.sample .env

# Update .env
IMAGE_DIR=/path/of/your/image/dir

docker compose up -d
```

### Development

```bash
cd searchy
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Executing program

```bash
# Copy default environment variables
cp .env.sample .env

# Update .env
IMAGE_DIR=/path/of/your/image/dir

python src/app.py
```

## Authors

Gregami - [git@gregami.com](mailto:git@gregami.com)

## License

This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/en/stable/#user-s-guide)
- [CLIP](https://huggingface.co/docs/transformers/v5.14.0/en/model_doc/clip)
- [Valkey](https://valkey.io/commands/)
