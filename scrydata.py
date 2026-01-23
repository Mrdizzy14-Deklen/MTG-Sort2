import requests

# Slims down card data
def slim_card_data(card: dict) -> dict:
    return {
        "name": card.get("name"),
        "uuid": card.get("id"),
        "colors": " ".join(card.get("colors", [])),
        "cmc": card.get("cmc")
    }

# Gets all cards from Scryfall
def get_catalog():
    print("Getting full catalog")
    download = requests.get("https://api.scryfall.com/bulk-data/default-cards").json()["download_uri"]
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
    print(f"Total cards downloaded: {len(cards_data)}")

    card_list = []

    for card in cards_data:
        slim_card = slim_card_data(card)
        card_list.append(slim_card)

    return card_list