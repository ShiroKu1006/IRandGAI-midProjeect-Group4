from flask import Flask, request


def create_app(search=None):
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/search")
    def search_route():
        query = request.args.get("q", "").strip()
        if not query:
            return {"error": "invalid_query"}, 400
        if search is None:
            return {"error": "search_unavailable"}, 503

        indexed_count, hits = search(query, 10)
        results = [
            {field: hit[field] for field in ("title", "url", "snippet", "score")}
            for hit in hits
        ]
        return {"indexed_count": indexed_count, "results": results}

    return app


app = create_app()
