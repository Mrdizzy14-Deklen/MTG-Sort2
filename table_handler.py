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
            cmc INTEGER,
            image_url TEXT,
            type_line TEXT,
            oracle_text TEXT,
            rarity TEXT,
            power INTEGER,
            toughness INTEGER,
            mana_cost TEXT,
            set_code TEXT,
            artist TEXT,
            flavor_text TEXT
        )
    ''')

    # Card list
    c.execute('''
        CREATE TABLE IF NOT EXISTS card_list (
            name TEXT,
            uuid TEXT UNIQUE PRIMARY KEY,
            quantity INTEGER DEFAULT 1,
            pile INTEGER
        )
    ''')
    
    # Deck list (for building decks)
    c.execute('''
        CREATE TABLE IF NOT EXISTS deck_list (
            name TEXT,
            uuid TEXT UNIQUE PRIMARY KEY,
            quantity INTEGER DEFAULT 1
        )
    ''')

    # Migrate old schema if needed
    migrate_schema(c)
    
    conn.commit()
    conn.close()

def migrate_schema(cursor=None):
    """Migrate old schema to new schema if needed"""
    if cursor is None:
        conn = utils.get_connection()
        c = conn.cursor()
        should_close = True
    else:
        c = cursor
        conn = None
        should_close = False
    
    try:
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_list'")
        if not c.fetchone():
            # Table doesn't exist yet, no migration needed
            return
        
        # Check current schema
        table_info = c.execute('PRAGMA table_info(card_list)').fetchall()
        columns = {col[1]: col[2] for col in table_info}
        
        needs_migration = False
        
        # Check if owner column exists (old schema)
        if 'owner' in columns:
            needs_migration = True
        
        # Check if pile is TEXT instead of INTEGER
        if 'pile' in columns and columns['pile'] == 'TEXT':
            needs_migration = True
        
        # Check if card_catalog needs additional columns
        catalog_info = c.execute('PRAGMA table_info(card_catalog)').fetchall()
        catalog_columns = {col[1]: col[2] for col in catalog_info}
        
        # Add missing columns
        new_columns = {
            'image_url': 'TEXT',
            'type_line': 'TEXT',
            'oracle_text': 'TEXT',
            'rarity': 'TEXT',
            'power': 'INTEGER',
            'toughness': 'INTEGER',
            'mana_cost': 'TEXT',
            'set_code': 'TEXT',
            'artist': 'TEXT',
            'flavor_text': 'TEXT'
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in catalog_columns:
                print(f"Adding {col_name} column to card_catalog...")
                try:
                    c.execute(f'ALTER TABLE card_catalog ADD COLUMN {col_name} {col_type}')
                    if conn:
                        conn.commit()
                except Exception as e:
                    print(f"Note: {col_name} column may already exist: {e}")
        
        if needs_migration:
            print("Migrating card_list table schema...")
            # Backup existing data
            c.execute('CREATE TABLE IF NOT EXISTS card_list_backup AS SELECT * FROM card_list')
            
            # Get all data (handle both old and new schemas)
            if 'owner' in columns:
                # Old schema with owner - select without owner column
                old_data = c.execute('SELECT name, uuid, quantity, pile FROM card_list').fetchall()
            else:
                old_data = c.execute('SELECT name, uuid, quantity, pile FROM card_list').fetchall()
            
            # Drop and recreate table with correct schema
            c.execute('DROP TABLE card_list')
            c.execute('''
                CREATE TABLE card_list (
                    name TEXT,
                    uuid TEXT UNIQUE PRIMARY KEY,
                    quantity INTEGER DEFAULT 1,
                    pile INTEGER
                )
            ''')
            
            # Restore data, converting pile to integer if needed
            for row in old_data:
                name, uuid, quantity, pile = row
                # Convert pile to integer if it's text or None
                try:
                    pile_int = int(pile) if pile is not None else 0
                except (ValueError, TypeError):
                    pile_int = 0
                
                c.execute('''
                    INSERT INTO card_list (name, uuid, quantity, pile)
                    VALUES (?, ?, ?, ?)
                ''', (name, uuid, quantity, pile_int))
            
            # Drop backup
            c.execute('DROP TABLE IF EXISTS card_list_backup')
            if conn:
                conn.commit()
            print("Schema migration completed successfully")
    
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if should_close and conn:
            conn.close()