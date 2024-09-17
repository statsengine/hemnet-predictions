import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from urllib.parse import quote

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

def scrape_hemnet(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    listings = []
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
                    'exact_address': None,
                    'price': None,
                    'size': None,
                    'rooms': None,
                    'monthly_fee': None,
                    'price_per_sqm': None,
                    'location': None,
                    'has_elevator': False,
                    'has_balcony': False,
                    'ending_price': None,
                    'price_change_percentage': None,
                    'ending_price_per_sqm': None
                }
                
                listing['exact_address'] = safe_find(item, 'h2', class_='hcl-card__title')
                listing['location'] = safe_find(item, 'div', class_='Location_address___eOo4')
                
                # Extract size and rooms
                size_rooms = item.find_all('p', class_='Text_hclText__V01MM Text_hclTextMedium__5uIGY')
                if len(size_rooms) >= 2:
                    listing['size'] = sanitize_size(size_rooms[0].text)
                    listing['rooms'] = sanitize_rooms(size_rooms[1].text)
                
                # Extract monthly fee
                monthly_fee = safe_find(item, 'span', class_='Text_hclText__V01MM')
                listing['monthly_fee'] = sanitize_fee(monthly_fee)
                
                # Extract features (elevator and balcony)
                features = item.find_all('span', class_='Label_hclLabelFeature__1_H8e')
                listing['has_elevator'] = 'Hiss' in [feature.text.strip() for feature in features]
                listing['has_balcony'] = 'Balkong' in [feature.text.strip() for feature in features]
                
                # Extract ending price information
                ending_price_div = item.find('div', class_='SellingPriceAttributes_contentWrapper__VaxX9')
                if ending_price_div:
                    ending_price = ending_price_div.find('span', class_='Text_hclText__V01MM Text_hclTextMedium__5uIGY')
                    if ending_price:
                        listing['ending_price'] = sanitize_price(ending_price.text)
                    
                    price_change = ending_price_div.find_all('span', class_='Text_hclText__V01MM Text_hclTextMedium__5uIGY')
                    if len(price_change) > 1:
                        listing['price_change_percentage'] = price_change[1].text.strip()
                    
                    ending_price_per_sqm = ending_price_div.find('p', class_='Text_hclText__V01MM')
                    if ending_price_per_sqm:
                        listing['ending_price_per_sqm'] = sanitize_price_per_sqm(ending_price_per_sqm.text)
                
                listings.append(listing)
            
            print(f"Scraped page {page}")
            page += 1
            print(f"Added {len(listings)} listings")
            time.sleep(1)  # Delay to be polite to the server
            
            if page == 50:
                break

        except Exception as e:
            print(f"Error scraping page {page}: {str(e)}")
            break
    
    return listings

def save_to_csv(listings, filename):
    if not listings:
        print("No listings to save.")
        return

    fieldnames = ['exact_address', 'price', 'size', 'rooms', 'monthly_fee', 'price_per_sqm', 
                  'location', 'has_elevator', 'has_balcony', 'ending_price', 
                  'price_change_percentage', 'ending_price_per_sqm']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for listing in listings:
            writer.writerow(listing)

url = 'https://www.hemnet.se/salda/bostader?location_ids%5B%5D=18031'
listings = scrape_hemnet(url)
save_to_csv(listings, 'hemnet_sold_listings.csv')

print("Scraping completed. Data saved to 'hemnet_sold_listings.csv'")