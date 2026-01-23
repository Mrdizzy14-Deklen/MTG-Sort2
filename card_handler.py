import utils
import hashlib

def h32(s):
    return int(hashlib.blake2s(s.encode('utf-8'), digest_size=4).hexdigest(), 16)

# Find pile for given card
def pile_index_oracle(card_in, pileNum):

    vBins = pileNum * 128
    oHash = h32(card_in)

    return (oHash % vBins) % pileNum

# Add card to collection
def add_card(card_in, owner, quantity=1):
    conn = utils.get_connection()
    c = conn.cursor()
    card = c.execute('SELECT * FROM card_catalog WHERE name = :name', {"name": card_in}).fetchone()
    pile_num = c.execute('SELECT pile_num FROM users WHERE username = :username', {"username": owner}).fetchone()
    pile = pile_index_oracle(card_in, pile_num[0])
    try:
        c.execute('''
            INSERT INTO card_list (name, uuid, quantity, owner, pile)
            VALUES (:name, :uuid, :quantity, :owner, :pile)
            ON CONFLICT(owner, uuid) DO UPDATE SET
                quantity = quantity + :quantity
        ''', {"name": card[0], "uuid": card[1], "quantity": quantity, "owner": owner, "pile": pile})

        conn.commit()
        print(f"Added {card_in} into Pile {pile}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
