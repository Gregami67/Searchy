import threading

from flask import Flask, render_template, request, send_from_directory

from searchy import Searchy
from searchy.attributes import IMAGE_COUNT, IMAGE_DIR, WATCHDOG

app = Flask(__name__)
searchy = Searchy(IMAGE_DIR)

if WATCHDOG:
    t = threading.Thread(target=searchy.watch, args=[IMAGE_DIR], daemon=True)
    t.start()


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
    count = int(count) if count else IMAGE_COUNT

    results = searchy.search(query, page, count)
    return results


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)
