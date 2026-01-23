import sqlite3

# Connect to database
def get_connection():
    conn = sqlite3.connect('cards.db')
    # conn.row_factory = sqlite3.Row
    return conn