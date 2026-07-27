import os as _os

from flask import Flask, abort, json, render_template, request, send_file

from ai import load_model_and_processor, search_embeddings

app = Flask(__name__)
model, processor, device = load_model_and_processor("cpu")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}
    query = (data.get("q") or "").strip()
    page = data.get("page", 1)

    if not query:
        return json.jsonify(
            {"image_paths": [], "total": 0, "has_next": False, "has_prev": False}
        )

    result = search_embeddings(query, processor, model, device)
    image_paths = [_os.path.basename(path) for path, _ in result]
    total = len(image_paths)
    per_page = 30
    start = (page - 1) * per_page
    end = start + per_page
    paginated = image_paths[start:end]
    has_next = end < total
    has_prev = page > 1

    return json.jsonify(
        {
            "image_paths": paginated,
            "total": total,
            "has_next": has_next,
            "has_prev": has_prev,
            "search_query": query,
            "page": page,
        }
    )


@app.route("/images/<path:filename>")
def serve_image(filename):
    image_dir = "./images"
    filepath = _os.path.join(image_dir, _os.path.basename(filename))
    if not _os.path.abspath(filepath).startswith(_os.path.abspath(image_dir)):
        abort(403)
    return send_file(filepath)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
