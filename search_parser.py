# Parses Scryfall-like search queries

import re
import utils

def parse_query(query):
    """
    Parse Scryfall-like search query into SQL conditions.
    Supports Scryfall syntax:
    - name:lightning or n:lightning (exact name match)
    - name:"Lightning Bolt" (exact phrase)
    - lightning (fuzzy name search)
    - cmc:3 or mv:3 (converted mana cost/mana value)
    - cmc:>=3 (comparison operators: <, >, <=, >=, !=)
    - c:red or color:red (card colors)
    - id:W,U or identity:W,U (color identity)
    - commander:W,U (commander color identity - filters cards within commander colors)
    - t:creature or type:creature (card type)
    - o:text or oracle:text (oracle text search)
    - r:rare or rarity:rare (rarity: common, uncommon, rare, mythic)
    - pow:3 or power:3 (power)
    - tou:3 or toughness:3 (toughness)
    - quantity:>0 (quantity in collection)
    - pile:3 (specific pile number)
    """
    if not query or not query.strip():
        return {}
    
    conditions = {}
    query = query.strip()
    
    # Parse field:value patterns - improved to handle multi-word values
    # Strategy: Find all field: patterns, then extract values until next field: or end
    matches = []
    remaining_query = query
    
    # Find all field: positions
    field_pattern = r'(\w+):'
    field_positions = []
    for match in re.finditer(field_pattern, query):
        field_positions.append((match.start(), match.end(), match.group(1)))
    
    # Extract values for each field
    removed_ranges = []
    for i, (start, end, field) in enumerate(field_positions):
        # Find where this value ends (start of next field: or end of string)
        if i + 1 < len(field_positions):
            value_end = field_positions[i + 1][0]
        else:
            value_end = len(query)
        
        # Extract the value (everything between field: and next field:)
        value_part = query[end:value_end].strip()
        
        # Handle quoted values
        actual_value_end = value_end
        if value_part.startswith('"'):
            # Find the closing quote
            quote_pos = value_part.find('"', 1)
            if quote_pos > 0:
                value = value_part[1:quote_pos]
                actual_value_end = end + quote_pos + 2  # Adjust for quotes
            else:
                value = value_part.strip('"')
        else:
            # Unquoted value - take everything up to next field:
            value = value_part
        
        # Remove quotes if present and clean up
        value = value.strip('"').strip()
        
        if value:
            matches.append((field, value))
            removed_ranges.append((start, actual_value_end))
    
    # Build remaining query by removing all matched patterns
    # Sort ranges by start position (descending) to remove from end to start
    removed_ranges.sort(reverse=True)
    for start, end in removed_ranges:
        remaining_query = remaining_query[:start] + remaining_query[end:]
    
    remaining_query = remaining_query.strip()
    
    for field, value in matches:
        value = value.strip('"')
        
        # Name search (n: or name:)
        if field in ['name', 'n']:
            conditions['name'] = value
        # CMC/Mana Value (cmc: or mv:)
        elif field in ['cmc', 'mv']:
            # Handle comparison operators
            if '>=' in value:
                conditions['cmc_min'] = int(value.replace('>=', ''))
            elif '<=' in value:
                conditions['cmc_max'] = int(value.replace('<=', ''))
            elif '>' in value:
                conditions['cmc_min'] = int(value.replace('>', '')) + 1
            elif '<' in value:
                conditions['cmc_max'] = int(value.replace('<', '')) - 1
            elif '!=' in value:
                conditions['cmc_not'] = int(value.replace('!=', ''))
            else:
                conditions['cmc'] = int(value)
        # Colors (c: or color:)
        elif field in ['colors', 'c', 'color']:
            # Handle color combinations
            colors = [c.strip().upper() for c in value.split(',')]
            conditions['colors'] = colors
        # Color Identity (id: or identity:)
        elif field in ['id', 'identity']:
            identity_colors = [c.strip().upper() for c in value.split(',')]
            conditions['color_identity'] = identity_colors
        # Commander color identity
        elif field == 'commander':
            commander_colors = [c.strip().upper() for c in value.split(',')]
            conditions['commander_colors'] = commander_colors
        # Type (t: or type:)
        elif field in ['t', 'type']:
            conditions['type'] = value.lower()
        # Oracle text (o: or oracle:)
        # Split by spaces and treat each word as a separate keyword that must match
        elif field in ['o', 'oracle']:
            # Split by spaces and filter out empty strings
            # Each token will be searched for independently (e.g., "{t}, sac draw" -> ["{t},", "sac", "draw"])
            oracle_keywords = [word.strip().lower() for word in value.split() if word.strip()]
            if oracle_keywords:
                conditions['oracle'] = oracle_keywords
        # Rarity (r: or rarity:)
        elif field in ['r', 'rarity']:
            conditions['rarity'] = value.lower()
        # Power (pow: or power:)
        elif field in ['pow', 'power']:
            try:
                value = value.strip()
                if '>=' in value:
                    conditions['power_min'] = int(value.replace('>=', '').strip())
                elif '<=' in value:
                    conditions['power_max'] = int(value.replace('<=', '').strip())
                elif '>' in value:
                    conditions['power_min'] = int(value.replace('>', '').strip()) + 1
                elif '<' in value:
                    conditions['power_max'] = int(value.replace('<', '').strip()) - 1
                elif '!=' in value:
                    conditions['power_not'] = int(value.replace('!=', '').strip())
                else:
                    conditions['power'] = int(value.strip())
            except (ValueError, AttributeError):
                # Invalid power value, skip this filter
                pass
        # Toughness (tou: or toughness:)
        elif field in ['tou', 'toughness']:
            try:
                value = value.strip()
                if '>=' in value:
                    conditions['toughness_min'] = int(value.replace('>=', '').strip())
                elif '<=' in value:
                    conditions['toughness_max'] = int(value.replace('<=', '').strip())
                elif '>' in value:
                    conditions['toughness_min'] = int(value.replace('>', '').strip()) + 1
                elif '<' in value:
                    conditions['toughness_max'] = int(value.replace('<', '').strip()) - 1
                elif '!=' in value:
                    conditions['toughness_not'] = int(value.replace('!=', '').strip())
                else:
                    conditions['toughness'] = int(value.strip())
            except (ValueError, AttributeError):
                # Invalid toughness value, skip this filter
                pass
        # Quantity
        elif field == 'quantity':
            # Handle quantity comparisons
            if '>=' in value:
                conditions['quantity_min'] = int(value.replace('>=', ''))
            elif '<=' in value:
                conditions['quantity_max'] = int(value.replace('<=', ''))
            elif '>' in value:
                conditions['quantity_min'] = int(value.replace('>', '')) + 1
            elif '<' in value:
                conditions['quantity_max'] = int(value.replace('<', '')) - 1
            elif '!=' in value:
                conditions['quantity_not'] = int(value.replace('!=', ''))
            else:
                conditions['quantity'] = int(value)
        # Mana Cost (m: or mana:)
        elif field in ['m', 'mana', 'mana_cost']:
            conditions['mana_cost'] = value.upper()
        # Set (set: or s:)
        elif field in ['set', 's', 'e']:
            conditions['set'] = value.lower()
        # Format (format: or f:)
        elif field in ['format', 'f']:
            conditions['format'] = value.lower()
        # Artist (artist: or a:)
        elif field in ['artist', 'a']:
            conditions['artist'] = value.lower()
        # Flavor text (flavor: or ft:)
        elif field in ['flavor', 'ft']:
            conditions['flavor'] = value.lower()
        # Pile
        elif field == 'pile':
            try:
                conditions['pile'] = int(value)
            except ValueError:
                pass
    
    # If there's remaining text after removing field patterns, treat as name search
    if remaining_query:
        conditions['name_fuzzy'] = remaining_query
    # If no field patterns found, treat entire query as name search
    elif not matches and query:
        conditions['name_fuzzy'] = query
    
    return conditions

def build_sql_query(conditions):
    """
    Build SQL query from parsed conditions.
    Returns (sql_query, params_dict)
    """
    base_query = '''
        SELECT cl.name, cl.uuid, cl.quantity, 
               COALESCE(cl.pile, 0) as pile, 
               cc.colors, cc.cmc, cc.image_url, cc.type_line, 
               cc.oracle_text, cc.rarity, cc.power, cc.toughness, cc.mana_cost,
               cc.set_code, cc.artist, cc.flavor_text
        FROM card_list cl
        JOIN card_catalog cc ON cl.uuid = cc.uuid
    '''
    
    where_clauses = []
    params = {}
    
    if 'name' in conditions:
        where_clauses.append('cl.name = :name')
        params['name'] = conditions['name']
    elif 'name_fuzzy' in conditions:
        where_clauses.append('cl.name LIKE :name_fuzzy')
        params['name_fuzzy'] = f"%{conditions['name_fuzzy']}%"
    
    if 'cmc' in conditions:
        where_clauses.append('cc.cmc = :cmc')
        params['cmc'] = conditions['cmc']
    elif 'cmc_min' in conditions or 'cmc_max' in conditions or 'cmc_not' in conditions:
        if 'cmc_min' in conditions:
            where_clauses.append('cc.cmc >= :cmc_min')
            params['cmc_min'] = conditions['cmc_min']
        if 'cmc_max' in conditions:
            where_clauses.append('cc.cmc <= :cmc_max')
            params['cmc_max'] = conditions['cmc_max']
        if 'cmc_not' in conditions:
            where_clauses.append('cc.cmc != :cmc_not')
            params['cmc_not'] = conditions['cmc_not']
    
    if 'colors' in conditions:
        # Check if card has all specified colors
        for i, color in enumerate(conditions['colors']):
            where_clauses.append(f'cc.colors LIKE :color_{i}')
            params[f'color_{i}'] = f"%{color}%"
    
    if 'color_identity' in conditions:
        # Similar to commander but for general color identity
        identity_color_set = set(conditions['color_identity'])
        all_colors = ['W', 'U', 'B', 'R', 'G']
        color_conditions = []
        for color in all_colors:
            if color not in identity_color_set:
                color_conditions.append(f"(cc.colors IS NULL OR cc.colors = '' OR cc.colors NOT LIKE :identity_exclude_{color})")
                params[f'identity_exclude_{color}'] = f"%{color}%"
        if color_conditions:
            where_clauses.append('(' + ' AND '.join(color_conditions) + ')')
    
    if 'commander_colors' in conditions:
        # Filter cards whose color identity is within commander's color identity
        # A card is valid if all its colors are in the commander's color set
        # Also allow colorless cards (empty or NULL colors)
        commander_color_set = set(conditions['commander_colors'])
        all_colors = ['W', 'U', 'B', 'R', 'G']
        
        # Build condition: card must not have any color outside commander's colors
        # This means: for each color NOT in commander's set, card must not have it
        color_conditions = []
        for color in all_colors:
            if color not in commander_color_set:
                # Card must not contain this color
                color_conditions.append(f"(cc.colors IS NULL OR cc.colors = '' OR cc.colors NOT LIKE :commander_exclude_{color})")
                params[f'commander_exclude_{color}'] = f"%{color}%"
        
        if color_conditions:
            where_clauses.append('(' + ' AND '.join(color_conditions) + ')')
    
    if 'type' in conditions:
        where_clauses.append('(cc.type_line IS NOT NULL AND cc.type_line != \'\' AND LOWER(cc.type_line) LIKE :type)')
        params['type'] = f"%{conditions['type']}%"
    
    if 'oracle' in conditions:
        # Oracle text: each keyword must appear somewhere in the text
        # This allows searching for "{t}, sac draw" and finding cards with all three terms
        oracle_keywords = conditions['oracle']
        if isinstance(oracle_keywords, list):
            # Multiple keywords - all must match
            oracle_conditions = []
            for i, keyword in enumerate(oracle_keywords):
                oracle_conditions.append('LOWER(cc.oracle_text) LIKE :oracle_{}'.format(i))
                params[f'oracle_{i}'] = f"%{keyword}%"
            where_clauses.append('(cc.oracle_text IS NOT NULL AND cc.oracle_text != \'\' AND {})'.format(' AND '.join(oracle_conditions)))
        else:
            # Single keyword (backward compatibility)
            where_clauses.append('(cc.oracle_text IS NOT NULL AND cc.oracle_text != \'\' AND LOWER(cc.oracle_text) LIKE :oracle)')
            params['oracle'] = f"%{conditions['oracle']}%"
    
    if 'rarity' in conditions:
        where_clauses.append('(cc.rarity IS NOT NULL AND cc.rarity != \'\' AND LOWER(cc.rarity) = :rarity)')
        params['rarity'] = conditions['rarity']
    
    if 'power' in conditions:
        where_clauses.append('(cc.power IS NOT NULL AND cc.power = :power)')
        params['power'] = conditions['power']
    elif 'power_min' in conditions or 'power_max' in conditions or 'power_not' in conditions:
        if 'power_min' in conditions:
            where_clauses.append('(cc.power IS NOT NULL AND cc.power >= :power_min)')
            params['power_min'] = conditions['power_min']
        if 'power_max' in conditions:
            where_clauses.append('(cc.power IS NOT NULL AND cc.power <= :power_max)')
            params['power_max'] = conditions['power_max']
        if 'power_not' in conditions:
            where_clauses.append('(cc.power IS NULL OR cc.power != :power_not)')
            params['power_not'] = conditions['power_not']
    
    if 'toughness' in conditions:
        where_clauses.append('(cc.toughness IS NOT NULL AND cc.toughness = :toughness)')
        params['toughness'] = conditions['toughness']
    elif 'toughness_min' in conditions or 'toughness_max' in conditions or 'toughness_not' in conditions:
        if 'toughness_min' in conditions:
            where_clauses.append('(cc.toughness IS NOT NULL AND cc.toughness >= :toughness_min)')
            params['toughness_min'] = conditions['toughness_min']
        if 'toughness_max' in conditions:
            where_clauses.append('(cc.toughness IS NOT NULL AND cc.toughness <= :toughness_max)')
            params['toughness_max'] = conditions['toughness_max']
        if 'toughness_not' in conditions:
            where_clauses.append('(cc.toughness IS NULL OR cc.toughness != :toughness_not)')
            params['toughness_not'] = conditions['toughness_not']
    
    if 'quantity' in conditions:
        where_clauses.append('cl.quantity = :quantity')
        params['quantity'] = conditions['quantity']
    elif 'quantity_min' in conditions or 'quantity_max' in conditions or 'quantity_not' in conditions:
        if 'quantity_min' in conditions:
            where_clauses.append('cl.quantity >= :quantity_min')
            params['quantity_min'] = conditions['quantity_min']
        if 'quantity_max' in conditions:
            where_clauses.append('cl.quantity <= :quantity_max')
            params['quantity_max'] = conditions['quantity_max']
        if 'quantity_not' in conditions:
            where_clauses.append('cl.quantity != :quantity_not')
            params['quantity_not'] = conditions['quantity_not']
    
    if 'mana_cost' in conditions:
        where_clauses.append('(cc.mana_cost IS NOT NULL AND cc.mana_cost != \'\' AND UPPER(cc.mana_cost) LIKE :mana_cost)')
        params['mana_cost'] = f"%{conditions['mana_cost']}%"
    
    if 'set' in conditions:
        where_clauses.append('(cc.set_code IS NOT NULL AND cc.set_code != \'\' AND LOWER(cc.set_code) = :set)')
        params['set'] = conditions['set']
    
    if 'artist' in conditions:
        # Note: artist field needs to be added to database schema
        where_clauses.append('(cc.artist IS NOT NULL AND cc.artist != \'\' AND LOWER(cc.artist) LIKE :artist)')
        params['artist'] = f"%{conditions['artist']}%"
    
    if 'flavor' in conditions:
        # Note: flavor_text field needs to be added to database schema
        where_clauses.append('(cc.flavor_text IS NOT NULL AND cc.flavor_text != \'\' AND LOWER(cc.flavor_text) LIKE :flavor)')
        params['flavor'] = f"%{conditions['flavor']}%"
    
    if 'pile' in conditions:
        where_clauses.append('cl.pile = :pile')
        params['pile'] = conditions['pile']
    
    if where_clauses:
        base_query += ' WHERE ' + ' AND '.join(where_clauses)
    
    base_query += ' ORDER BY cl.name'
    
    return base_query, params

def execute_search(query_string):
    """
    Parse query string and execute search, returning results.
    Returns list of tuples: (name, uuid, quantity, pile, colors, cmc)
    """
    conditions = parse_query(query_string)
    sql_query, params = build_sql_query(conditions)
    
    conn = utils.get_connection()
    c = conn.cursor()
    try:
        results = c.execute(sql_query, params).fetchall()
    except Exception as e:
        print(f"ERROR executing SQL: {e}")
        print(f"SQL: {sql_query}")
        print(f"Params: {params}")
        raise
    finally:
        conn.close()
    
    return results
