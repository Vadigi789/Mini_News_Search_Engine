import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)


# Create a connection pool
connection_pool = psycopg2.pool.SimpleConnectionPool(
    1, 10,
    host="aws-1-ap-southeast-2.pooler.supabase.com",
    database="postgres",
    user="postgres.isurklczfsdjdfeyrvxx",
    password = os.environ["DB_PASSWORD"],
    port=6543,
    sslmode="require"
)


def get_connection():
    return connection_pool.getconn()


def release_connection(conn):
    connection_pool.putconn(conn)


def insert_document(title, url, content):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            INSERT INTO documents (title, url, content, search_vector)
            VALUES (
                %s,
                %s,
                %s,
                to_tsvector('english', %s)
            )
            ON CONFLICT (url) DO NOTHING
            RETURNING id;
        """, (title, url, content, content))

        result = cur.fetchone()

        conn.commit()

        if result:
            return result[0]

        return None

    except Exception as e:

        print("Database error:", e)
        conn.rollback()
        return None

    finally:

        cur.close()
        release_connection(conn)


def get_documents_by_ids(doc_ids):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT id, title, url, content
            FROM documents
            WHERE id = ANY(%s);
        """, (doc_ids,))

        rows = cur.fetchall()

        return {row[0]: (row[1], row[2], row[3]) for row in rows}

    except Exception as e:

        print("Database error:", e)
        return {}

    finally:

        cur.close()

        release_connection(conn)
