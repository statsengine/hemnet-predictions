import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from urllib.parse import quote, urljoin

def safe_find(item, *args, **kwargs):
    try:
        element = item.find(*args, **kwargs)
        return element.text.strip() if element else None
    except AttributeError:
        return None

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def sanitize_price(price_str):
    if price_str:
        return safe_int(re.sub(r'[^\d]', '', price_str))
    return None

def sanitize_size(size_str):
    if size_str:
        return safe_float(size_str.replace(',', '.').split()[0])
    return None

def sanitize_rooms(rooms_str):
    if rooms_str:
        rooms_num = rooms_str.replace(',', '.').split()[0]
        return safe_float(rooms_num)
    return None

def sanitize_floor(floor_str):
    if floor_str:
        match = re.search(r'\d+', floor_str)
        if match:
            return safe_int(match.group())
    return 1  # Default to 1 if no floor information is provided

def sanitize_fee(fee_str):
    if fee_str:
        return safe_int(re.sub(r'[^\d]', '', fee_str))
    return None

def sanitize_price_per_sqm(price_per_sqm_str):
    if price_per_sqm_str:
        return safe_int(re.sub(r'[^\d]', '', price_per_sqm_str))
    return None

def sanitize_address(address_str):
    if address_str:
        return address_str.split(',', 1)[0].strip()
    return address_str

def scrape_hemnet(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    listings = []
    skipped_listings = 0
    page = 1
    while True:
        try:
            response = requests.get(f"{url}&page={page}", headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('a', class_='hcl-card')
            if not items:
                break
            for item in items:
                listing = {
                    'link': None,
                    'exact_address': None,
                    'price': None,
                    'size': None,
                    'rooms': None,
                    'floor': None,
                    'monthly_fee': None,
                    'price_per_sqm': None,
                    'location': None,
                    'has_elevator': False,
                    'has_balcony': False,
                }
                
                # Extract the link
                listing['link'] = urljoin('https://www.hemnet.se', item.get('href'))
                
                # Extract and sanitize exact_address
                raw_address = safe_find(item, 'h2', class_='hcl-card__title')
                listing['exact_address'] = sanitize_address(raw_address)
                
                attributes = item.find_all('span', class_='ForSaleAttributes_primaryAttributes__tqSRJ')
                if attributes:
                    listing['price'] = sanitize_price(attributes[0].text.strip() if len(attributes) > 0 else None)
                    listing['size'] = sanitize_size(attributes[1].text.strip() if len(attributes) > 1 else None)
                    listing['rooms'] = sanitize_rooms(attributes[2].text.strip() if len(attributes) > 2 else None)
                    listing['floor'] = sanitize_floor(attributes[3].text.strip() if len(attributes) > 3 else None)
                
                secondary_attributes = item.find_all('span', class_='ForSaleAttributes_secondaryAttributes__ko6y2')
                if secondary_attributes:
                    listing['monthly_fee'] = sanitize_fee(secondary_attributes[0].text.strip() if len(secondary_attributes) > 0 else None)
                    listing['price_per_sqm'] = sanitize_price_per_sqm(secondary_attributes[1].text.strip() if len(secondary_attributes) > 1 else None)
                
                listing['location'] = safe_find(item, 'div', class_='Location_address___eOo4')
                
                features = item.find_all('span', class_='Label_hclLabelFeature__1_H8e')
                listing['has_elevator'] = 'Hiss' in [feature.text.strip() for feature in features]
                listing['has_balcony'] = 'Balkong' in [feature.text.strip() for feature in features]
                
                # Only add listings with both exact_address and price
                if listing['exact_address'] and listing['price']:
                    listings.append(listing)
                else:
                    skipped_listings += 1
                    print(f"Skipped listing due to missing {'exact_address' if not listing['exact_address'] else 'price'}")
            
            print(f"Scraped page {page}")
            print(f"Total listings collected: {len(listings)}")
            print(f"Total listings skipped: {skipped_listings}")
            page += 1
            time.sleep(1)  # Delay to be polite to the server
            
            if page == 50:
                break

        except Exception as e:
            print(f"Error scraping page {page}: {str(e)}")
            break
    
    print(f"Scraping completed. Total listings collected: {len(listings)}")
    print(f"Total listings skipped: {skipped_listings}")
    return listings

def save_to_csv(listings, filename):
    if not listings:
        print("No listings to save.")
        return

    fieldnames = ['link', 'exact_address', 'price', 'size', 'rooms', 'floor', 'monthly_fee', 'price_per_sqm', 
                  'location', 'has_elevator', 'has_balcony', 'latitude', 'longitude']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for listing in listings:
            writer.writerow(listing)

url = 'https://www.hemnet.se/bostader?item_types%5B%5D=bostadsratt&location_ids%5B%5D=18031'
listings = scrape_hemnet(url)
save_to_csv(listings, 'hemnet_listings.csv')

print("Scraping completed. Data saved to 'hemnet_listings.csv'")