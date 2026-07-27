import os

from flask import Flask, abort, json, render_template, request, send_file

from searchy import Searchy
from searchy.tools import tools

IMAGE_DIR = "../images"

app = Flask(__name__)
searchy = Searchy(IMAGE_DIR)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json()

    query = data.get("query")
    if not query:
        return "Missing query", 400

    page = request.args.get("page")
    if not page:
        return "Missing page", 400
    page = int(page)

    count = request.args.get("count")
    count = int(count) if count else Searchy.COUNT

    results = searchy.search(query, page, count)
    return results


@app.route("/images/<path:filename>")
def serve_image(filename):
    filepath = os.path.join(IMAGE_DIR, os.path.basename(filename))
    if not os.path.abspath(filepath).startswith(os.path.abspath(IMAGE_DIR)):
        abort(403)
    return send_file(filepath)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
