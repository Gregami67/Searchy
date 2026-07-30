import logging
import threading

import torch
from flask import Flask, render_template, request, send_from_directory
from flask.logging import default_handler
from PIL import Image

from searchy import Searchy
from searchy.attributes import DEBUG, IMAGE_COUNT, IMAGE_DIR, WATCHDOG

app = Flask(__name__)

logger = logging.getLogger("searchy")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.addHandler(default_handler)

searchy = Searchy(IMAGE_DIR)

if WATCHDOG:
    t = threading.Thread(target=searchy.watch, args=[IMAGE_DIR], daemon=True)
    t.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(silent=True) or {}

    query = data.get("query")
    img = None

    if not query:
        image = request.files.get("image")

        if image:
            img = Image.open(image.stream).convert("RGB")
        else:
            return "Missing query or image", 400

    query = None if img else query

    page = request.args.get("page")
    if not page:
        return "Missing page", 400
    page = int(page)

    count = request.args.get("count")
    count = int(count) if count else IMAGE_COUNT

    results = searchy.search(query, img, page, count)
    return results


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)
