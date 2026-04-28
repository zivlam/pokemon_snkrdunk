import os
import time
import requests
import socket
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import urllib3

# Ignore urllib3 OpenSSL warnings
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

# --- Initialize Firebase Admin ---
# Assumes serviceAccountKey.json is in the same directory (set up via GitHub Actions)
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Successfully connected to Firebase!")
except Exception as e:
    print(f"⚠️ Firebase initialization failed: {e}")
    db = None

def check_dns(hostname):
    """Diagnose DNS resolution status"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def format_to_hk_time(utc_date_str):
    """Convert UTC time string to Hong Kong time (UTC+8)"""
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
    Fetch SNKRDUNK trading history for cards, filter for PSA10, calculate HKD pricing,
    and push the updated data directly to Firebase.
    """
    hostname = "snkrdunk.com"
    HKD_RATE = 0.051 # Set JPY to HKD exchange rate
    
    if not check_dns(hostname):
        print(f"❌ Network Warning: Could not resolve {hostname}.")
        return

    url = f"https://{hostname}/en/v1/products/SW---{product_id}/trading-histories"
    
    # Securely fetch Cookie from GitHub Secrets / Environment Variables
    raw_cookies = os.environ.get('SNKRDUNK_COOKIE')
    if not raw_cookies:
        print("❌ Error: SNKRDUNK_COOKIE environment variable not found! Please check your GitHub Secrets.")
        return

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cookie': raw_cookies,
        'referer': f'https://{hostname}/en/trading-cards/{product_id}',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    params = {'perPage': 12, 'page': 1, 'used': 'true'}

    try:
        print(f"🔍 Requesting data for ID: {product_id}...")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            histories = data.get('histories') or data.get('data') or data.get('tradingHistories')
            
            if not histories:
                print(f"⚠️ No trading history found for {product_id}.")
                return

            parsed_history = []
            
            for item in histories:
                raw_date = (item.get('tradedAt') or item.get('tradeDate') or 
                            item.get('createdAt') or item.get('created_at') or 
                            item.get('date') or item.get('soldAt') or item.get('sold_at'))
                
                price = item.get('price', '0')
                cond = item.get('condition') or item.get('state') or 'N/A'
                
                # Enforce PSA 10 Filtering
                if filter_psa10 and "PSA" not in cond.upper() and "10" not in str(cond):
                    continue

                hk_time = format_to_hk_time(raw_date)

                # Calculate HKD Conversion
                try:
                    price_val = int(price)
                    hkd_val = int(price_val * HKD_RATE)
                except:
                    hkd_val = 0
                
                parsed_history.append({
                    'id': len(parsed_history) + 1,
                    'date': hk_time,
                    'condition': cond,
                    'priceHKD': hkd_val
                })
            
            if not parsed_history:
                print(f"⚠️ No PSA 10 records found for {product_id}.")
                return

            # Push the compiled data to Firebase
            if db:
                current_price = parsed_history[0]['priceHKD']
                doc_ref = db.collection('snkrdunk_cards').document(product_id)
                
                # 🌟 CRITICAL FIX: We use SERVER_TIMESTAMP here so the React App knows exactly when the script ran!
                doc_ref.set({
                    'currentPriceHKD': current_price,
                    'history': parsed_history,
                    'lastUpdated': firestore.SERVER_TIMESTAMP 
                }, merge=True)
                
                print(f"✅ Successfully updated {product_id} to Firebase!")
            else:
                print(f"⚠️ Could not write {product_id} to Firebase (No DB connection).")
                
        else:
            print(f"❌ Error fetching {product_id}: HTTP Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception occurred while processing {product_id}: {e}")

if __name__ == "__main__":
    # Hardcoded Fallback Tracking List
    cards_to_track = [
        '730952', '722239', '141410', '325078', '395201', '657364', '128085', '100092', '100090', '93381', '91243', '91246', '93078', '91155', '776365', '115267', '98531', '724996', '186243', '455596', '328774', '776371', '704385', '91252', '663638', '107450', '91425', '704401', '730956', '107448', '91260', '520383', '91423', '120250', '93015', '91227', '721965', '91377', '674418', '618446', '128181', '455595', '585213', '704407', '744298', '230981', '289056', '91163', '164250', '607941', '618445', '618447', '657365', '186428', '128147', '128121', '128101', '396405', '93096', '131236', '408333', '128212', '663661', '607471', '91119', '459741', '91178', '91118', '185276', '601144', '105553', '91127', '253253', '601146', '606347', '106796', '104514', '91176', '104548', '91422', '91538', '390544', '127035', '93092', '149334', '180170', '128092', '132270', '132284', '91283', '387059', '128117', '146897', '132279',
        '502986', '91158', '488418', '128231', '162095', '105568', '91192', '91191', '103079', '91156', '124080', '135232', '332792', '326267', '469628', '141445', '671484', '156432', '126676', '292564', '292565', '674424', '199043', '489823', '485638', '505952', '407397', '106802', '116069', '418741', '160147', '103080', '111868', '454071', '518774', '128089', '671486', '475194', '332798', '705192', '100081', '104784', '134393', '671489', '545622', '103803', '105005', '392953', '98529', '641578', '671488', '135980', '91159', '103771', '124079', '671483', '141443', '141444', '470986', '396076', '601145', '91160', '91157', '98530', '601147'
    ]
    
    print("🚀 Starting automated scraping task...")
    
    # Fetch dynamically added IDs from Firebase (Adds custom cards from React UI)
    dynamic_ids = []
    if db:
        try:
            docs = db.collection('snkrdunk_cards').stream()
            dynamic_ids = [doc.id for doc in docs]
            print(f"📦 Found {len(dynamic_ids)} total cards currently tracked in Firebase.")
        except Exception as e:
            print(f"⚠️ Could not fetch dynamic IDs from Firebase: {e}")

    # Combine hardcoded and dynamic IDs, then remove duplicates
    all_tracking_ids = list(set(cards_to_track + dynamic_ids))
    print(f"🔍 Total unique cards to scrape and update: {len(all_tracking_ids)}")

    for card_id in all_tracking_ids:
        update_card_to_firebase(card_id)
        time.sleep(2)  # Pause to avoid rate limits and getting blocked
        
    print("🏁 Automated task completed!")
