import time
import scrydata
import card_handler
import utils
import table_handler
import user_handler
import window_handler

# Gets all new cards since last run
def update_catalog():
    conn = utils.get_connection()
    c = conn.cursor()

    # Get last update
    date = c.execute('SELECT value FROM metadata WHERE key = "date"').fetchone()

    # Update catalog based on last update
    if date:
        card_data = scrydata.get_catalog_updates(date)
    else:
        card_data = scrydata.get_catalog()

    # Insert each card
    for card in card_data:
        c.execute('''
            INSERT OR IGNORE INTO card_catalog (name, uuid, colors, cmc)
            VALUES (:name, :uuid, :colors, :cmc)
        ''', {"name": card["name"], "uuid": card["uuid"], "colors": card["colors"], "cmc": card.get("cmc")})
    
    # Update last update date
    c.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ("date", :value)
    ''', {"value": time.strftime("%Y-%m-%d")})

    conn.commit()
    conn.close()

def prechecks():
    table_handler.setup_tables()
    update_catalog()


if __name__ == "__main__":
    prechecks()
    window_handler.gui()

    conn = utils.get_connection()
    c = conn.cursor()
    conn.commit()

    user_handler.add_user("John", "Opt", 4)

    cards = c.execute('SELECT * FROM users ORDER BY pile_num DESC').fetchmany(10)
    print(cards)
    conn.close()