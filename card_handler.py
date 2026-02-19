# Handles operations related to cards in collection

import utils
import hashlib

def h32(s):
    return int(hashlib.blake2s(s.encode('utf-8'), digest_size=4).hexdigest(), 16)

def get_pile_num():
    """Get the number of piles from metadata"""
    conn = utils.get_connection()
    c = conn.cursor()
    result = c.execute('SELECT value FROM metadata WHERE key = "pile_num"').fetchone()
    conn.close()
    if result:
        return int(result[0])
    return 4  # Default to 4 piles if not set

def set_pile_num(pile_num):
    """Set the number of piles in metadata and recalculate all card piles"""
    conn = utils.get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ("pile_num", :value)
    ''', {"value": str(pile_num)})
    
    # Recalculate piles for all existing cards
    cards = c.execute('SELECT uuid FROM card_list').fetchall()
    for (uuid,) in cards:
        new_pile = pile_index_oracle(uuid, pile_num)
        c.execute('''
            UPDATE card_list SET pile = :pile WHERE uuid = :uuid
        ''', {"pile": new_pile, "uuid": uuid})
    
    conn.commit()
    conn.close()

# Find pile for given card UUID
def pile_index_oracle(card_uuid, pileNum):
    """Calculate which pile a card belongs to based on its UUID"""
    vBins = pileNum * 128
    oHash = h32(card_uuid)
    return (oHash % vBins) % pileNum

# Add card to collection
def add_card(card_name, quantity=1):
    """Add a card to the collection and assign it to a pile. Returns (success: bool, message: str)"""
    conn = utils.get_connection()
    c = conn.cursor()
    
    # Check if card exists in catalog
    card = c.execute('SELECT * FROM card_catalog WHERE name = :name', {"name": card_name}).fetchone()
    if not card:
        conn.close()
        return False, f"Card '{card_name}' not found in catalog."
    
    pile_num = get_pile_num()
    pile = pile_index_oracle(card[1], pile_num)  # Use UUID for hashing
    
    try:
        c.execute('''
            INSERT INTO card_list (name, uuid, quantity, pile)
            VALUES (:name, :uuid, :quantity, :pile)
            ON CONFLICT(uuid) DO UPDATE SET
                quantity = quantity + :quantity
        ''', {"name": card[0], "uuid": card[1], "quantity": quantity, "pile": pile})

        conn.commit()
        print(f"Added {card_name} to collection - Pile {pile}")
        conn.close()
        return True, f"Added {quantity}x {card_name} to collection (Pile {pile})", pile
    except Exception as e:
        conn.rollback()
        conn.close()
        error_msg = f"Error adding card: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return False, error_msg

def get_card_pile(card_uuid):
    """Get the pile number for a card by its UUID"""
    pile_num = get_pile_num()
    return pile_index_oracle(card_uuid, pile_num)

def remove_card(card_name, quantity=1):
    """Remove cards from the collection"""
    conn = utils.get_connection()
    c = conn.cursor()
    card = c.execute('SELECT * FROM card_catalog WHERE name = :name', {"name": card_name}).fetchone()
    if not card:
        print(f"Error: Card {card_name} not found in catalog.")
        conn.close()
        return False
    
    # Check current quantity
    current = c.execute('SELECT quantity FROM card_list WHERE uuid = :uuid', {"uuid": card[1]}).fetchone()
    if not current:
        print(f"Card {card_name} not in collection.")
        conn.close()
        return False
    
    current_qty = current[0]
    new_qty = max(0, current_qty - quantity)
    
    if new_qty == 0:
        # Remove card entirely
        c.execute('DELETE FROM card_list WHERE uuid = :uuid', {"uuid": card[1]})
        print(f"Removed {card_name} from collection")
    else:
        # Update quantity
        c.execute('''
            UPDATE card_list SET quantity = :quantity WHERE uuid = :uuid
        ''', {"quantity": new_qty, "uuid": card[1]})
        print(f"Removed {quantity} of {card_name} from collection (now {new_qty})")
    
    conn.commit()
    conn.close()
    return True

def remove_card_by_uuid(uuid, quantity=1):
    """Remove cards from the collection by UUID"""
    conn = utils.get_connection()
    c = conn.cursor()
    
    # Check current quantity
    current = c.execute('SELECT quantity, name FROM card_list WHERE uuid = :uuid', {"uuid": uuid}).fetchone()
    if not current:
        print(f"Card not in collection.")
        conn.close()
        return False
    
    current_qty, card_name = current
    new_qty = max(0, current_qty - quantity)
    
    if new_qty == 0:
        # Remove card entirely
        c.execute('DELETE FROM card_list WHERE uuid = :uuid', {"uuid": uuid})
        print(f"Removed {card_name} from collection")
    else:
        # Update quantity
        c.execute('''
            UPDATE card_list SET quantity = :quantity WHERE uuid = :uuid
        ''', {"quantity": new_qty, "uuid": uuid})
        print(f"Removed {quantity} of {card_name} from collection (now {new_qty})")
    
    conn.commit()
    conn.close()
    return True

def search_catalog(query=""):
    """Search the card catalog (not collection) for adding cards"""
    conn = utils.get_connection()
    c = conn.cursor()
    
    if query:
        results = c.execute('''
            SELECT name FROM card_catalog
            WHERE name LIKE :query
            ORDER BY name
            LIMIT 50
        ''', {"query": f"%{query}%"}).fetchall()
    else:
        results = c.execute('''
            SELECT name FROM card_catalog
            ORDER BY name
            LIMIT 50
        ''').fetchall()
    
    conn.close()
    return [row[0] for row in results]

def get_unique_sets():
    """Get unique set codes from the card catalog"""
    conn = utils.get_connection()
    c = conn.cursor()
    
    results = c.execute('''
        SELECT DISTINCT set_code FROM card_catalog
        WHERE set_code IS NOT NULL AND set_code != ''
        ORDER BY set_code
    ''').fetchall()
    
    conn.close()
    return [row[0] for row in results]

# -----------------------------
# Deck list helpers (deckbuilding)
# -----------------------------

def deck_add_card(uuid, name, quantity=1):
    """Add a card to the deck list (increments quantity). Returns (success, message)."""
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        # Check available quantity in collection
        result = c.execute('SELECT quantity FROM card_list WHERE uuid = ?', (uuid,)).fetchone()
        if not result:
            conn.close()
            return False, "Card not in collection"
        
        available_qty = result[0]
        
        # Check current quantity in deck list
        deck_result = c.execute('SELECT quantity FROM deck_list WHERE uuid = ?', (uuid,)).fetchone()
        current_deck_qty = deck_result[0] if deck_result else 0
        
        # Check if adding would exceed available quantity
        if current_deck_qty + quantity > available_qty:
            conn.close()
            return False, f"Only {available_qty} available (already have {current_deck_qty} in list)"
        
        # Add to deck list
        c.execute('''
            INSERT INTO deck_list (name, uuid, quantity)
            VALUES (:name, :uuid, :quantity)
            ON CONFLICT(uuid) DO UPDATE SET
                quantity = quantity + :quantity,
                name = :name
        ''', {"name": name, "uuid": uuid, "quantity": int(quantity)})
        conn.commit()
        return True, f"Added {quantity}x {name}"
    except Exception as e:
        print(f"Error adding to deck list: {e}")
        conn.rollback()
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def deck_clear():
    """Remove all cards from the deck list."""
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM deck_list')
        conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing deck list: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def deck_remove_card(uuid, quantity=1):
    """Remove a card from the deck list. Returns (success, message)."""
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        # Check current quantity in deck list
        result = c.execute('SELECT quantity, name FROM deck_list WHERE uuid = ?', (uuid,)).fetchone()
        if not result:
            conn.close()
            return False, "Card not in deck list"
        
        current_qty, name = result
        new_qty = max(0, current_qty - quantity)
        
        if new_qty == 0:
            # Remove card entirely
            c.execute('DELETE FROM deck_list WHERE uuid = ?', (uuid,))
            conn.commit()
            conn.close()
            return True, f"Removed {name} from deck list"
        else:
            # Update quantity
            c.execute('UPDATE deck_list SET quantity = ? WHERE uuid = ?', (new_qty, uuid))
            conn.commit()
            conn.close()
            return True, f"Removed {quantity}x {name} from deck list"
    except Exception as e:
        print(f"Error removing from deck list: {e}")
        conn.rollback()
        conn.close()
        return False, f"Error: {str(e)}"

def deck_get_all():
    """Get deck list entries as list of (name, uuid, quantity, pile)."""
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        # Join with card_list to get pile information
        return c.execute('''
            SELECT dl.name, dl.uuid, dl.quantity, COALESCE(cl.pile, 0) as pile
            FROM deck_list dl
            LEFT JOIN card_list cl ON dl.uuid = cl.uuid
            ORDER BY dl.name
        ''').fetchall()
    finally:
        conn.close()

def deck_total_cards():
    """Total quantity of cards in deck list."""
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        row = c.execute('SELECT COALESCE(SUM(quantity), 0) FROM deck_list').fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()

def deck_remove_all_from_collection():
    """Remove all cards in deck list from the collection. Returns (success, message, count)."""
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        # Get all cards in deck list
        deck_cards = c.execute('SELECT uuid, quantity FROM deck_list').fetchall()
        if not deck_cards:
            conn.close()
            return True, "No cards in list", 0
        
        removed_count = 0
        for uuid, qty in deck_cards:
            # Remove from collection
            current = c.execute('SELECT quantity FROM card_list WHERE uuid = ?', (uuid,)).fetchone()
            if current:
                current_qty = current[0]
                new_qty = max(0, current_qty - qty)
                if new_qty == 0:
                    c.execute('DELETE FROM card_list WHERE uuid = ?', (uuid,))
                else:
                    c.execute('UPDATE card_list SET quantity = ? WHERE uuid = ?', (new_qty, uuid))
                removed_count += min(qty, current_qty)
        
        # Clear deck list
        c.execute('DELETE FROM deck_list')
        conn.commit()
        conn.close()
        return True, f"Removed {removed_count} card(s) from collection", removed_count
    except Exception as e:
        print(f"Error removing cards from collection: {e}")
        conn.rollback()
        conn.close()
        return False, f"Error: {str(e)}", 0

if __name__ == "__main__":
    conn = utils.get_connection()
    c = conn.cursor()
    results = c.execute('SELECT * FROM card_list').fetchall()
    conn.close()
    print(results)