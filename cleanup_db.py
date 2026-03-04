from database import get_connection

def cleanup():

    conn = get_connection()
    cur = conn.cursor()

    query = """
    DELETE FROM documents
    WHERE created_at < NOW() - INTERVAL '7 days';
    """

    cur.execute(query)

    deleted = cur.rowcount

    conn.commit()

    cur.close()
    conn.close()

    print(f"Deleted {deleted} old documents")


if __name__ == "__main__":
    cleanup()
