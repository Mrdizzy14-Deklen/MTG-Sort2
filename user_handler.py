# Handles operations related to users

import utils

# Add user to database
def add_user(username, card_code, pile_num):
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO users (username, card_code, pile_num)
            VALUES (:username, :card_code, :pile_num)
        ''', {"username": username, "card_code": card_code, "pile_num": pile_num})
        conn.commit()
        print(f"Added user {username}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def check_login(username, card_code):
    conn = utils.get_connection()
    c = conn.cursor()
    user = c.execute('SELECT * FROM users WHERE username = :username', {"username": username}).fetchone()
    conn.close()
    if user and user[1] == card_code:
        return True
    return False
