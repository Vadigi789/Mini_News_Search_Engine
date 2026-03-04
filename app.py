from flask import Flask, render_template, request
from search import search

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():

    results = []
    query = ""
    page = 1

    if request.method == "POST":

        query = request.form.get("query", "").strip()
        page = int(request.form.get("page", 1))

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

    # pagination logic
    results_per_page = 10
    start = (page - 1) * results_per_page
    end = start + results_per_page

    page_results = results[start:end]

    has_next = end < len(results)

    return render_template(
        "index.html",
        results=page_results,
        query=query,
        page=page,
        has_next=has_next
    )


if __name__ == "__main__":
    app.run(debug=True)
