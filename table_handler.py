# Used to setup tables in the database

import utils

# Setup tables
def setup_tables():
    conn = utils.get_connection()
    c = conn.cursor()

    # Metadata table
    c.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Card catalog
    c.execute('''
        CREATE TABLE IF NOT EXISTS card_catalog (
            name TEXT PRIMARY KEY,
            uuid TEXT UNIQUE,
            colors TEXT,
            cmc INTEGER
        )
    ''')

    # Card list
    c.execute('''
        CREATE TABLE IF NOT EXISTS card_list (
            name TEXT,
            uuid TEXT,
            quantity INTEGER DEFAULT 0,
            owner TEXT,
            pile TEXT,
            PRIMARY KEY (owner, uuid)
        )
    ''')

    # User table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT UNIQUE PRIMARY KEY,
            card_code TEXT,
            pile_num INTEGER
        )
    ''')

    conn.commit()
    conn.close()