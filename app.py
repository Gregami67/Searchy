from flask import Flask, request

from ai import load_model_and_processor, search_embeddings

app = Flask(__name__)
model, processor, device = load_model_and_processor("cpu")


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    query = data.get("query")

    if not query:
        return "query field required", 400

    result = search_embeddings(query, processor, model, device)
    image_paths = [path for path, _ in result]

    return image_paths
