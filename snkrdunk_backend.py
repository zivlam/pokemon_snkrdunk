#!/usr/bin/env python3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket
from datetime import datetime, timedelta
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import urllib3
import time

# Disable urllib3 OpenSSL warnings
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

# Initialize Firebase
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"❌ Firebase initialization failed (check if serviceAccountKey.json exists): {e}")
    db = None

def check_dns(hostname):
    """Check DNS resolution status"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def format_to_hk_time(utc_date_str):
    """Convert UTC date string to Hong Kong Time (UTC+8)"""
    if not utc_date_str or utc_date_str == 'Unknown':
        return 'Unknown'
    try:
        date_str = str(utc_date_str).replace('Z', '').split('.')[0]
        if 'T' in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        
        hk_dt = dt + timedelta(hours=8)
        return hk_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(utc_date_str).replace('T', ' ').split('.')[0]

def update_card_to_firebase(product_id, filter_psa10=True):
    """
    Fetch SNKRDUNK trading history, filter for strictly PSA 10, 
    keep only 3 days of history, and upload to Firebase
    """
    hostname = "snkrdunk.com"
    url = f"https://{hostname}/en/v1/products/SW---{product_id}/trading-histories"
    
    ip = check_dns(hostname)
    if not ip:
        print(f"[Network Warning] Cannot resolve {hostname}.")
        return

    # Fetch Cookie from Environment Variables
    raw_cookies = os.environ.get('SNKRDUNK_COOKIE')
    if not raw_cookies:
        print("❌ Error: Cookie not found. Please ensure the SNKRDUNK_COOKIE environment variable is set.")
        return

    retry_strategy = Retry(total=3, backoff_factor=2)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cookie': raw_cookies,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    }
    
    # Increase perPage to 100 to ensure we get enough raw records to extract 30 valid PSA 10s
    params = {'perPage': 100, 'page': 1, 'used': 'true'}

    try:
        print(f"Fetching data (ID: {product_id})...")
        response = session.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            histories = data.get('histories') or data.get('tradingHistories') or data.get('data')
            
            if histories is None:
                print(f"[Warning] No data list found for ID {product_id}.\n")
                return

            parsed_history = []
            latest_price = 0
            
            for item in histories:
                # Stop collecting once we have 30 valid PSA 10 records
                if len(parsed_history) >= 30:
                    break

                cond = item.get('condition') or item.get('state') or 'N/A'
                
                # Strictly filter for PSA 10 (removes spaces to match 'PSA 10' or 'PSA10' and ignores PSA 9)
                cond_formatted = str(cond).upper().replace(" ", "")
                if filter_psa10 and "PSA10" not in cond_formatted: 
                    continue

                raw_date = item.get('tradedAt') or item.get('createdAt') or item.get('soldAt')
                hk_time = format_to_hk_time(raw_date)
                
                # Get native HKD price
                price_hkd = int(item.get('price', 0))

                # Always assign the first matched PSA 10 record as the latest price
                if latest_price == 0: 
                    latest_price = price_hkd

                parsed_history.append({
                    "id": len(parsed_history) + 1,
                    "date": hk_time,
                    "condition": "PSA 10",
                    "priceHKD": price_hkd
                })

            # Print the formatted clean English table
            if parsed_history:
                print(f"{'Date (HKT)':<20} | {'Condition':<10} | {'Price (HKD)'}")
                print("-" * 55)
                for record in parsed_history:
                    print(f"{record['date']:<20} | {record['condition']:<10} | HK${record['priceHKD']}")
                print("-" * 55)

            if db:
                # Always push to Firebase to initialize the document, even if history is empty
                doc_ref = db.collection('snkrdunk_cards').document(str(product_id))
                doc_ref.set({
                    'id': str(product_id),
                    'currentPriceHKD': latest_price,
                    'history': parsed_history,
                    'lastUpdated': firestore.SERVER_TIMESTAMP
                }, merge=True) 
                
                if parsed_history:
                    print(f"✅ Card {product_id} successfully pushed! Latest Price: HK${latest_price}\n")
                else:
                    print(f"⚠️ Card {product_id} pushed with HK$0 (No recent PSA 10 records).\n")
                    
        else:
            print(f"❌ Error: Status code {response.status_code} for ID {product_id}\n")
            
    except Exception as e:
        print(f"[Exception occurred]: {e}\n")

if __name__ == "__main__":
    # Complete list of all old and new card IDs with corrected True SNKRDUNK IDs
    cards_to_track = [
        '730952', '722239', '141410', '325078', '395201', '657364', '128085', '100092', '100090', '93381', '91243', 
        '91246', '93078', '91155', '776365', '115267', '98531', '724996', '186243', '455596', '328774', '776371', 
        '704385', '91252', '663638', '107450', '91425', '704401', '730956', '107448', '91260', '520383', '91423', 
        '120250', '93015', '91227', '721965', '91377', '674418', '618446', '128181', '455595', '585213', '704407', 
        '744298', '230981', '289056', '91163', '164250', '607941', '618445', '618447', '657365', '186428', '128147', 
        '128121', '128101', '396405', '93096', '131236', '408333', '128212', '663661', '607471', '91119', '459741', 
        '91178', '91118', '185276', '601144', '105553', '91127', '253253', '601146', '606347', '106796', '104514', 
        '91176', '104548', '91422', '91538', '390544', '127035', '93092', '149334', '180170', '128092', '132270', 
        '132284', '91283', '387059', '128117', '146897', '132279',
        # --- Newly Added Missing Cards ---
        '502986', '91158', '488418', '128231', '162095', '105568', '91192', '91191', '103079', '91156', '124080', 
        '135232', '332792', '326267', '469628', '141445', '671484', '156432', '126676', '292564', '292565', '674424', 
        '199043', '489823', '485638', '505956', '505952', '407397', '106802', '116069', '418741', '160147', '103080', 
        '111868', '454071', '518774', '128089', '671486', '475194', '332798', '705192', '100081', '104784', '134393', 
        '671489', '545622', '91134', '103803', '105005', '392953', '98529', 
        '641578', '671488', '135980', '91159', '103771', '124079', '671483', '141443', '141444', '470986', '396076', 
        '601145', '91160', '91157', '98530', '601147'
    ]
    
    print("🚀 Starting automated scraping task...")
    for card_id in cards_to_track:
        update_card_to_firebase(card_id)
        time.sleep(2)  # Pause for 2 seconds between requests to avoid getting blocked
        
    print("🏁 Automated task completed!")
