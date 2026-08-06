import threading

from flask import Flask, abort, render_template, request, send_from_directory
from PIL import Image

from searchy import Searchy
from searchy.config import IMAGE_COUNT, IMAGE_DIR, THUMB_DIR, WATCHDOG

app = Flask(__name__)
searchy = Searchy(IMAGE_DIR)

if WATCHDOG:
    t = threading.Thread(target=searchy.watch, args=[IMAGE_DIR], daemon=True)
    t.start()


@app.route("/")
def index():
    return render_template("index.html")


def _get_search_args() -> tuple[int, int]:
    page = request.args.get("page")

    if not page:
        abort(400, description="Missing page")

    page = int(page)
    count = request.args.get("count")
    count = int(count) if count else IMAGE_COUNT

    return page, count


@app.route("/api/search/text", methods=["POST"])
def search_by_text():
    data = request.get_json()
    query = data.get("query")
    page, count = _get_search_args()

    original, thumb = searchy.search(page, count, query=query)
    return {"original_name": original, "thumb_name": thumb}


@app.route("/api/search/image", methods=["POST"])
def search_by_image():
    image = request.files.get("image")

    if not image:
        abort(400, description="Missing image")

    img = Image.open(image.stream).convert("RGB")
    page, count = _get_search_args()

    original, thumb = searchy.search(page, count, image=img)
    return {"original_name": original, "thumb_name": thumb}


@app.route("/api/search/name", methods=["POST"])
def search_by_name():
    data = request.get_json()
    name = data.get("name")
    page, count = _get_search_args()

    original, thumb = searchy.search_name(page, count, name)
    return {"original_name": original, "thumb_name": thumb}


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)


@app.route("/thumbs/<path:filename>")
def serve_thumb(filename):
    return send_from_directory(THUMB_DIR, filename)
