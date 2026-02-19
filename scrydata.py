import requests

# Slims down card data
def slim_card_data(card: dict) -> dict:
    # Get oracle text (from card_faces for double-faced cards)
    oracle_text = ""
    if "card_faces" in card and len(card.get("card_faces", [])) > 0:
        oracle_text = " // ".join([face.get("oracle_text", "") or "" for face in card.get("card_faces", [])])
    else:
        oracle_text = card.get("oracle_text", "") or ""
    
    # Get type line
    type_line = ""
    if "card_faces" in card and len(card.get("card_faces", [])) > 0:
        type_line = " // ".join([face.get("type_line", "") or "" for face in card.get("card_faces", [])])
    else:
        type_line = card.get("type_line", "") or ""
    
    # Get power/toughness (handle both single and double-faced)
    power = None
    toughness = None
    if "card_faces" in card and len(card.get("card_faces", [])) > 0:
        # For double-faced, use first face
        power_str = card.get("card_faces", [{}])[0].get("power")
        toughness_str = card.get("card_faces", [{}])[0].get("toughness")
    else:
        power_str = card.get("power")
        toughness_str = card.get("toughness")
    
    # Convert power/toughness to integers if possible
    try:
        power = int(power_str) if power_str and power_str.isdigit() else None
    except (ValueError, TypeError):
        power = None
    
    try:
        toughness = int(toughness_str) if toughness_str and toughness_str.isdigit() else None
    except (ValueError, TypeError):
        toughness = None
    
    # Get flavor text (from card_faces for double-faced cards)
    flavor_text = ""
    if "card_faces" in card and len(card.get("card_faces", [])) > 0:
        flavor_text = " // ".join([face.get("flavor_text", "") or "" for face in card.get("card_faces", [])])
    else:
        flavor_text = card.get("flavor_text", "") or ""
    
    return {
        "name": card.get("name"),
        "uuid": card.get("id"),
        "colors": " ".join(card.get("colors", [])),
        "cmc": card.get("cmc"),
        "image": card.get("image_uris", {}).get("normal") if "image_uris" in card else None,
        "type_line": type_line,
        "oracle_text": oracle_text,
        "rarity": card.get("rarity", ""),
        "power": power,
        "toughness": toughness,
        "mana_cost": card.get("mana_cost", "") or "",
        "set_code": card.get("set", ""),
        "artist": card.get("artist", "") or "",
        "flavor_text": flavor_text
    }

# Gets all cards from Scryfall
def get_catalog():
    print("Getting full catalog")
    download = requests.get("https://api.scryfall.com/bulk-data/oracle-cards").json()["download_uri"]
    cards_data = requests.get(download, stream=True).json()
    print(f"Total cards downloaded: {len(cards_data)}")

    card_list = []

    for card in cards_data:
        slim_card = slim_card_data(card)
        card_list.append(slim_card)
    
    return card_list

# Gets new cards since last run
def get_catalog_updates(last_updated: str):
    print(f"Getting updates since {last_updated[0]}")
    download = requests.get(f"https://api.scryfall.com/cards/search?q=date>={last_updated[0]}").json()
    cards_data = download.get("data", [])
    print(cards_data[0])
    print(f"Total cards downloaded: {len(cards_data)}")

    card_list = []

    for card in cards_data:
        slim_card = slim_card_data(card)
        card_list.append(slim_card)

    return card_list