#!/usr/bin/env python3
"""Extract SVG icon paths from Scryfall's advanced search page"""
import requests
import re
import os
from html.parser import HTMLParser

class SVGIconExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.svgs = {}
        self.current_section = None
        self.in_svg = False
        self.svg_content = []
        self.current_label = None
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Look for filter sections
        if tag == 'label' and attrs_dict.get('for'):
            self.current_label = attrs_dict.get('for', '')
        
        # Look for SVG elements
        if tag == 'svg':
            self.in_svg = True
            self.svg_content = ['<svg']
            # Add attributes
            for attr, value in attrs:
                self.svg_content.append(f'{attr}="{value}"')
            self.svg_content.append('>')
        
        # Look for path elements inside SVG
        if tag == 'path' and self.in_svg:
            path_attrs = ' '.join([f'{k}="{v}"' for k, v in attrs])
            self.svg_content.append(f'<path {path_attrs} />')
    
    def handle_endtag(self, tag):
        if tag == 'svg' and self.in_svg:
            self.svg_content.append('</svg>')
            svg_str = ' '.join(self.svg_content)
            
            # Try to match icon to section based on nearby label
            if self.current_label:
                # Map label names to our icon names
                label_to_icon = {
                    'card-name': 'card_name',
                    'oracle-text': 'text',
                    'type-line': 'type',
                    'colors': 'colors',
                    'commander': 'commander',
                    'mana-cost': 'mana_cost',
                    'mana-value': 'stats',
                    'set': 'sets',
                    'rarity': 'rarity',
                    'power': 'power',
                    'toughness': 'toughness',
                    'artist': 'artist',
                    'flavor-text': 'flavor',
                }
                
                icon_name = label_to_icon.get(self.current_label)
                if icon_name and icon_name not in self.svgs:
                    self.svgs[icon_name] = svg_str
            
            self.in_svg = False
            self.svg_content = []
    
    def handle_data(self, data):
        pass

def main():
    print("Fetching Scryfall advanced search page...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get('https://scryfall.com/advanced', headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Failed to fetch page: {response.status_code}")
            return
        
        print("Parsing HTML for SVG icons...")
        parser = SVGIconExtractor()
        parser.feed(response.text)
        
        print(f"Found {len(parser.svgs)} SVG icons")
        
        # Save icons
        os.makedirs('icons', exist_ok=True)
        for icon_name, svg_content in parser.svgs.items():
            filename = f'icons/{icon_name}.svg'
            with open(filename, 'w') as f:
                f.write(svg_content)
            print(f"Saved {filename}")
        
        print("\nDone! Icons extracted from Scryfall.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
