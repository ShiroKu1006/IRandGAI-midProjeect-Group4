from flask import Flask

app = Flask(__name__)


@app.get("/api/health")
def health():
    return {"status": "ok"}