import time
import scrydata
import card_handler
import utils
import table_handler
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

    # Batch insert for better performance
    print(f"Inserting {len(card_data)} cards into catalog...")
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(card_data), batch_size):
        batch = card_data[i:i+batch_size]
        c.executemany('''
            INSERT OR REPLACE INTO card_catalog 
            (name, uuid, colors, cmc, image_url, type_line, oracle_text, rarity, power, toughness, mana_cost, set_code, artist, flavor_text)
            VALUES (:name, :uuid, :colors, :cmc, :image_url, :type_line, :oracle_text, :rarity, :power, :toughness, :mana_cost, :set_code, :artist, :flavor_text)
        ''', [{
            "name": card["name"], 
            "uuid": card["uuid"], 
            "colors": card["colors"], 
            "cmc": card.get("cmc"),
            "image_url": card.get("image"),
            "type_line": card.get("type_line", ""),
            "oracle_text": card.get("oracle_text", ""),
            "rarity": card.get("rarity", ""),
            "power": card.get("power"),
            "toughness": card.get("toughness"),
            "mana_cost": card.get("mana_cost", ""),
            "set_code": card.get("set_code", ""),
            "artist": card.get("artist", ""),
            "flavor_text": card.get("flavor_text", "")
        } for card in batch])
        
        conn.commit()
        total_inserted += len(batch)
        print(f"Inserted {total_inserted}/{len(card_data)} cards...")
    
    # Update last update date
    c.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ("date", :value)
    ''', {"value": time.strftime("%Y-%m-%d")})

    # Initialize pile_num if not set
    pile_num = c.execute('SELECT value FROM metadata WHERE key = "pile_num"').fetchone()
    if not pile_num:
        c.execute('''
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ("pile_num", "4")
        ''')

    conn.commit()
    conn.close()
    print("Catalog update complete!")

def prechecks():
    table_handler.setup_tables()
    # Check if catalog needs updating (only if no date exists or date is old)
    conn = utils.get_connection()
    c = conn.cursor()
    date = c.execute('SELECT value FROM metadata WHERE key = "date"').fetchone()
    conn.close()
    
    # Only update catalog if it's missing or hasn't been updated today
    today = time.strftime("%Y-%m-%d")
    if not date or date[0] != today:
        print("Catalog update needed. This may take a moment...")
        update_catalog()
    else:
        print("Catalog is up to date. Skipping update.")


if __name__ == "__main__":
    print("Running prechecks...")
    prechecks()
    print("Prechecks complete. Starting GUI...")
    window_handler.gui()