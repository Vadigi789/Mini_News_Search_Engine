from database import get_connection

def search(query):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, url, content,
               ts_rank(search_vector, plainto_tsquery('english', %s)) AS score
        FROM documents
        WHERE search_vector @@ plainto_tsquery('english', %s)
        ORDER BY score DESC
        LIMIT 10;
    """, (query, query))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return results