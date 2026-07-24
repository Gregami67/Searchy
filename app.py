import os as _os

from flask import Flask, abort, render_template, request, send_file

from ai import load_model_and_processor, search_embeddings

app = Flask(__name__)
model, processor, device = load_model_and_processor("cpu")


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    image_paths = []

    if query:
        result = search_embeddings(query, processor, model, device)
        image_paths = [(path, _os.path.basename(path)) for path, _ in result]

    return render_template(
        "index.html",
        search_query=query or None,
        image_paths=image_paths,
    )


@app.route("/images/<path:filename>")
def serve_image(filename):
    image_dir = "./images"
    filepath = _os.path.join(image_dir, _os.path.basename(filename))
    if not _os.path.abspath(filepath).startswith(_os.path.abspath(image_dir)):
        abort(403)
    return send_file(filepath)


if __name__ == "__main__":
    app.run(debug=True)
