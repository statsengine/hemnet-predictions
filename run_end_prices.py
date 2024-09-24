import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime
from dateutil import parser
import locale

def safe_find(item, *args, **kwargs):
    try:
        element = item.find(*args, **kwargs)
        return element.text.strip() if element else None
    except AttributeError:
        return None

def sanitize_price(price_str):
    if price_str:
        try:
            return int(re.sub(r'[^\d]', '', price_str))
        except ValueError:
            print(f"Warning: Could not convert price to integer: {price_str}")
            return None
    return None

def sanitize_price_per_sqm(price_per_sqm_str):
    if price_per_sqm_str:
        try:
            return int(re.sub(r'[^\d]', '', price_per_sqm_str))
        except ValueError:
            print(f"Warning: Could not convert price per sqm to integer: {price_per_sqm_str}")
            return None
    return None

def sanitize_size(size_str):
    if size_str:
        # Try to extract the number part and ignore unexpected characters
        try:
            return float(re.search(r"[\d.,]+", size_str).group().replace(',', '.'))
        except (ValueError, AttributeError):
            print(f"Warning: Could not sanitize size: {size_str}")
            return None
    return None

def sanitize_rooms(rooms_str):
    if rooms_str:
        try:
            rooms_num = re.search(r"[\d.,]+", rooms_str).group().replace(',', '.')
            return float(rooms_num)
        except (ValueError, AttributeError):
            print(f"Warning: Could not sanitize rooms: {rooms_str}")
            return None
    return None

def sanitize_fee(fee_str):
    if fee_str:
        return int(re.sub(r'[^\d]', '', fee_str))
    return None

def sanitize_address(address_str):
    if address_str:
        return address_str.split(',', 1)[0].strip()
    return address_str

def parse_swedish_date(date_str):
    # Set locale to Swedish
    try:
        locale.setlocale(locale.LC_TIME, 'sv_SE.UTF-8')
    except locale.Error:
        # Fallback if the Swedish locale is not installed
        print("Swedish locale not found. Using default locale.")
    
    # Remove "Såld " from the beginning of the string
    date_str = date_str.replace("Såld ", "")
    
    # Parse the date
    date_obj = parser.parse(date_str, dayfirst=True)
    
    # Format the date as YYYY-MM-DD
    return date_obj.strftime('%Y-%m-%d')

def scrape_hemnet(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    listings = []
    skipped_listings = 0  # Counter for skipped listings
    page = 1
    while True:
        try:
            response = requests.get(f"{url}&page={page}", headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('a', class_='hcl-card')
            if not items:
                print("No more listings found. Ending scraping.")
                break
            for item in items:
                listing = {
                    'link': 'https://www.hemnet.se' + item.get('href', ''),  # Extract and store the full link
                    'exact_address': None,
                    'size': None,
                    'rooms': None,
                    'monthly_fee': None,
                    'location': None,
                    'has_elevator': False,
                    'has_balcony': False,
                    'listing_price': None,  # Initialize listing_price
                    'end_price': None,      # Initialize end_price
                    'price_change_percentage': None,
                    'price_per_sqm': None,
                    'date': None
                }
                
                # Extract and sanitize exact_address
                raw_address = safe_find(item, 'h2', class_='hcl-card__title')
                listing['exact_address'] = sanitize_address(raw_address)
                
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
                        listing['end_price'] = sanitize_price(ending_price.text)
                    
                    price_change = ending_price_div.find_all('span', class_='Text_hclText__V01MM Text_hclTextMedium__5uIGY')
                    if len(price_change) > 1:
                        price_change_text = price_change[1].text.strip()
                        try:
                            price_change_percentage = int(re.sub(r'[^\d]', '', price_change_text))
                            listing['price_change_percentage'] = price_change_percentage
                            
                            if listing['end_price'] is not None and listing['price_change_percentage'] is not None:
                                # Calculate listing_price
                                listing['listing_price'] = int(listing['end_price'] / (1 + listing['price_change_percentage'] / 100))
                        except ValueError:
                            print(f"Warning: Could not convert price change to integer: {price_change_text}")
                    
                    ending_price_per_sqm = ending_price_div.find('p', class_='Text_hclText__V01MM')
                    if ending_price_per_sqm:
                        listing['price_per_sqm'] = sanitize_price_per_sqm(ending_price_per_sqm.text)
                
                # Extract sale date
                sale_date = item.find('span', class_='Label_hclLabel__nITs3 Label_hclLabelSoldAt__gw0aX Label_hclLabelState__nKlGX')
                if sale_date:
                    listing['date'] = parse_swedish_date(sale_date.text)
                
                # Validation: Ensure 'exact_address' and 'end_price' are present
                if listing['exact_address'] and listing['end_price'] and listing['listing_price']:
                    listings.append(listing)
                else:
                    skipped_listings += 1
                    # Optional: Print reason for skipping
                    missing_fields = []
                    if not listing['exact_address']:
                        missing_fields.append('exact_address')
                    if not listing['end_price']:
                        missing_fields.append('end_price')
                    if not listing['listing_price']:
                        missing_fields.append('listing_price')
                    print(f"Skipping listing due to missing fields: {', '.join(missing_fields)}")
            
            print(f"Scraped page {page}")
            print(f"Total listings collected so far: {len(listings)}")
            print(f"Total listings skipped so far: {skipped_listings}")
            page += 1
            time.sleep(1)  # Delay to be polite to the server
            
            # For testing purposes, limit to 2 pages. Remove or adjust this condition as needed.
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

    fieldnames = ['link', 'exact_address', 'size', 'rooms', 'monthly_fee', 'location', 'has_elevator', 'has_balcony',
                  'listing_price', 'end_price', 'price_change_percentage', 'price_per_sqm', 'date']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for listing in listings:
            writer.writerow(listing)

# URL for sold properties in a specific location
url = 'https://www.hemnet.se/salda/bostader?location_ids%5B%5D=18031'

# Scrape the listings
listings = scrape_hemnet(url)

# Save the listings to a CSV file
save_to_csv(listings, 'hemnet_sold_listings.csv')

print("Scraping completed. Data saved to 'hemnet_sold_listings.csv'")
