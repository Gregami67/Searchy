from flask import current_app as app

from searchy.attributes import DEBUG


def run_dev():
    app.run(debug=DEBUG, host="0.0.0.0", use_reloader=False)


def run_prod():
    import subprocess

    subprocess.run(["gunicorn", "-b", "0.0.0.0", "app:app"])
