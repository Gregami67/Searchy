from searchy.attributes import DEBUG


def run_dev():
    from app import app

    app.run(debug=DEBUG, host="0.0.0.0", port=5000, use_reloader=False)


def run_prod():
    import subprocess

    subprocess.run(["gunicorn", "-b", "0.0.0.0:5000", "app:app"])
