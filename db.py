import streamlit as st
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Open and return a new MySQL connection using the credentials stored
    in st.session_state['db_config']. Returns None if not configured or if
    the connection fails (an error is shown in the app in that case)."""
    cfg = st.session_state.get("db_config")
    if not cfg:
        return None
    try:
        conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
        )
        return conn
    except Error as e:
        st.error(f"Could not connect to MySQL: {e}")
        return None


def run_query(sql, params=None, fetch=False):
    """Run a SELECT (fetch=True) or an INSERT/UPDATE/DELETE (fetch=False).

    - For SELECTs, returns a list of dict rows (or None on failure).
    - For INSERT/UPDATE/DELETE, commits and returns cursor.lastrowid
      (or None on failure).
    """
    conn = get_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
        cursor.close()
        return result
    except Error as e:
        st.error(f"Query failed: {e}")
        return None
    finally:
        conn.close()


def fetch_options(sql, id_field, label_field):
    """Return a dict of {display_label: id} for populating a selectbox
    from a parent table, e.g. fetch_options(
        "SELECT user_id, user_name FROM users", "user_id", "user_name"
    )."""
    rows = run_query(sql, fetch=True) or []
    return {f"{r[label_field]} (ID {r[id_field]})": r[id_field] for r in rows}