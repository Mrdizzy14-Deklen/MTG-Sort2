#!/usr/bin/env python3
"""Download filter icons from Scryfall advanced search page"""
import requests
import os

# Scryfall icon URLs - these are the actual icon paths from their site
icon_urls = {
    'card_name': 'https://scryfall.com/assets/icons/card.svg',
    'text': 'https://scryfall.com/assets/icons/book.svg',
    'type': 'https://scryfall.com/assets/icons/fingerprint.svg',
    'colors': 'https://scryfall.com/assets/icons/colors.svg',
    'commander': 'https://scryfall.com/assets/icons/shield.svg',
    'mana_cost': 'https://scryfall.com/assets/icons/mana.svg',
    'stats': 'https://scryfall.com/assets/icons/chart.svg',
    'sets': 'https://scryfall.com/assets/icons/crown.svg',
    'rarity': 'https://scryfall.com/assets/icons/star.svg',
    'power': 'https://scryfall.com/assets/icons/sword.svg',
    'toughness': 'https://scryfall.com/assets/icons/shield.svg',
    'artist': 'https://scryfall.com/assets/icons/paintbrush.svg',
    'flavor': 'https://scryfall.com/assets/icons/document.svg',
    'pile': 'https://scryfall.com/assets/icons/books.svg',
    'quantity': 'https://scryfall.com/assets/icons/numbers.svg',
}

def download_icon(url, filename):
    """Download an icon from URL"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return False

def main():
    os.makedirs('icons', exist_ok=True)
    
    print("Downloading icons from Scryfall...")
    downloaded = 0
    for name, url in icon_urls.items():
        filename = f'icons/{name}.svg'
        if download_icon(url, filename):
            print(f"✓ Downloaded {filename}")
            downloaded += 1
        else:
            print(f"✗ Failed to download {name}")
    
    print(f"\nDownloaded {downloaded}/{len(icon_urls)} icons")

if __name__ == '__main__':
    main()
