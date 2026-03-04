from flask import Flask, render_template, request
from search import search

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():

    results = []
    query = ""

    if request.method == "POST":

        query = request.form.get("query", "").strip()

        if query:

            docs = search(query)

            for doc_id, title, url, content, score in docs:

                snippet = content[:250] + "..."

                results.append({
                    "title": title,
                    "score": float(score),
                    "snippet": snippet,
                    "url": url
                })

    return render_template(
        "index.html",
        results=results,
        query=query
    )


if __name__ == "__main__":
    app.run(debug=True)