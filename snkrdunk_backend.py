#!/usr/bin/env python3
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import socket
import sys
from datetime import datetime, timedelta

# Ignore urllib3 OpenSSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

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
        date_str = utc_date_str.replace('Z', '').split('.')[0]
        if 'T' in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        
        hk_dt = dt + timedelta(hours=8)
        return hk_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return str(utc_date_str).replace('T', ' ').split('.')[0]

def update_card_to_firebase(product_id, filter_psa10=True):
    hostname = "snkrdunk.com"
    HKD_RATE = 0.051
    url = f"https://{hostname}/en/v1/products/SW---{product_id}/trading-histories"
    
    # 🌟 MODIFY HERE: Read the Cookie from system environment variables
    raw_cookies = os.environ.get('SNKRDUNK_COOKIE')
    
    if not raw_cookies:
        print("❌ Error: Cookie not found. Please check your environment variable settings.")
        return

def get_snkrdunk_trading_history(product_id, page=1, per_page=12, filter_psa10=True):
    """
    Fetch SNKRDUNK trading history for cards, filter for PSA10, and calculate HKD pricing
    """
    hostname = "snkrdunk.com"
    HKD_RATE = 0.051 # Set JPY to HKD exchange rate
    
    ip = check_dns(hostname)
    if not ip:
        print(f"【Network Warning】Could not resolve {hostname}.")
        return

    url = f"https://{hostname}/en/v1/products/SW---{product_id}/trading-histories"
    
    # Your Cookies
    raw_cookies = "ENSID=MTc3NjY2NTE1OXxneGFOVHlTTVFRNC1faGZxWTl1d19OZ0VON3ktSHU2ZmhRM1BPd3ZqMzhjdjA4bVl5N09hMmViU0l5dkM5dmJzSlFRcEZRdkswZE9UaUZYemc2R0FJTktBV0ZoekRJQm18vVArxJholQdsxibvkwffc-EZHHvCHoOeyKg-UdEgWC8=; _fbp=fb.1.1769565983830.427879144364123664; _tt_enable_cookie=1; _ttp=01KG15M59YDJSHSFC45QBRHQDR_.tt.1; _pin_unauth=dWlkPU1EZzBOakkzWWpJdFpERXdaaTAwT1dNeExUazBNVGd0TldObU5tWXpOVFUwTXpBMQ; _twpid=tw.1772682321818.472168692562332285; _yjsu_yjad=1774943045.d8267b4e-005c-4204-a4c4-a8f9b09389f6; __lt__cid=f0f7fa13-6fd0-47be-b95f-324511a6607d; ch-veil-id=61d01114-c420-4595-aaa6-eca810198423; _rp_uid=9aac201b-522c-e223-78ad-b2c2d342ecae; _gcl_au=1.1.1014333606.1769565984.482342097.1775805668.1775805699; _gid=GA1.2.348483311.1776658696; _dd_s=aid=fc298176-1ab0-4cf2-bbb2-cc1ff3f00604&logs=1&id=180ecbb0-3f94-4367-9007-313f63b62765&created=1776658694089&expire=1776660064044&rum=0; showHobbyItemHistory=3%3A722239; showAllItemHistory=3%3A722239; __lt__sid=3f34fddd-c490c9a7; _ga_T9G4FWRKGP=GS2.1.s1776664634$o3$g1$t1776664777$j60$l0$h0; _ga=GA1.1.1616533055.1769565984; __rtbh.uid=%7B%22eventType%22%3A%22uid%22%2C%22id%22%3A%22undefined%22%2C%22expiryDate%22%3A%222027-04-20T05%3A59%3A37.871Z%22%7D; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%220726jz1ltAeM4SCeldxG%22%2C%22expiryDate%22%3A%222027-04-20T05%3A59%3A37.871Z%22%7D; cto_bundle=e4GBiF80bVk4UFBsQk92TnBXd1Fvck5IJTJGS2RaSFZlbHdIaUg4a1dEeHhVUnhrUkJjeXc0ZXVhZkE3NmV1c0k2bUhrR2Q2cDNjZUxHWFczSzJCVUhBaDU4eHI4RG9xZ1JPMTFqT1VWSFRjeXM3bElyem92dWo2ZFFjbVVycEs5eFhPN1BUTWdWVUhBU1owZXg5aGQzbWZsWVlCSGpIUU43eWs3cWUxMDh0MkxLYjRjT3RjR2xUZzJTZDk1ckc2YXNZV1N4dw; ttcsid_CEM1KGBC77U8BHMFF6SG=1776664637338::BB8RWBa_enJxQu7gG6HM.3.1776664778758.1; _ga_WLFPCJHLHL=GS2.1.s1776664622$o3$g1$t1776664778$j46$l0$h0; forterToken=d6f7685db2bf4a64a9a140a35490a3d8_1776664777447__UDF43-m4_27ck_; _rdt_uuid=1769565983607.314899a4-a0f8-477e-9d7c-c35a61e9567f; _rdt_em=:30782d35084a2974fa61718e6d96c49d889ca5ec30b78c35d49e604e7665cb18,e985279d9155614f15428fd2ef60793fad1096a85e2b1292b6b90b3b1804729c,b9f533973eac86f3ba6e8ec3668baec2f2ad2272802be95d1f72c35fcd9c400c,f7404338803168ec5b7befc9b8dfc9f6f9aeb154d78eeec54d52ca37845e3de0; _derived_epik=dj0yJnU9U21tS1BPcWtyeU1PbmVteV9Pc09sbVczMF9MaWl4VUcmbj0waGRBb25wZExnaDE1MzAxM09IcVZ3Jm09MSZ0PUFBQUFBR25sd1NZJnJtPTEmcnQ9QUFBQUFHbmx3U1kmc3A9Mg; ttcsid_CAP79SBC77U56BB6BI50=1776664187089::ZALMf7lDv_52K66qmEXh.83.1776664871318.1; ttcsid=1776664185386::_ZVemd5ZmFqprwjoFMVs.85.1776664871317.0::1.683904.685620::667727.63.417.1473::686419.461.908; _ga_6H1EYVVN53=GS2.1.s1776664186$o89$g1$t1776665160$j60$l0$h0; _ga_3722WCREQR=GS2.1.s1776664186$o90$g1$t1776665160$j60$l0$h0"

    retry_strategy = Retry(total=3, backoff_factor=2)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-TW;q=0.7,zh;q=0.6',
        'cookie': raw_cookies,
        'referer': f'https://snkrdunk.com/en/trading-cards/{product_id}?slide=right',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
        'x-request-id': 'ThQCyOX12Qmy1AElad5k'
    }

    params = {'perPage': per_page, 'page': page, 'used': 'true'}

    try:
        print(f"Requesting data (ID: {product_id}, Page {page})...")
        response = session.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            histories = data.get('histories') or data.get('data') or data.get('tradingHistories')
            
            if not histories:
                print("【Warning】No data list found.")
                return

            print(f"{'Date (HKT)':<20} | {'Condition':<10} | {'HKD':<12} | {'JPY'}")
            print("-" * 65)
            
            found_count = 0
            for item in histories:
                raw_date = (item.get('tradedAt') or item.get('tradeDate') or 
                            item.get('createdAt') or item.get('created_at') or 
                            item.get('date') or item.get('soldAt') or item.get('sold_at'))
                
                price = item.get('price', '0')
                cond = item.get('condition') or item.get('state') or 'N/A'
                
                if filter_psa10 and "PSA" in cond.upper() and "10" in cond:
                    pass 
                elif filter_psa10:
                    continue

                hk_time = format_to_hk_time(raw_date)

                # Calculate and format HKD and JPY
                try:
                    price_val = int(price)
                    hkd_val = price_val * HKD_RATE
                    formatted_hkd = f"HK${hkd_val:,.2f}"
                    formatted_jpy = f"¥{price_val:,}"
                except:
                    formatted_hkd = "N/A"
                    formatted_jpy = f"¥{price}"
                
                print(f"{hk_time:<20} | {cond:<10} | {formatted_hkd:<12} | {formatted_jpy}")
                found_count += 1
            
            if found_count == 0:
                print("【Notice】No PSA 10 records on this page.")
        else:
            print(f"【Error】Status code: {response.status_code}")
            
    except Exception as e:
        print(f"【Exception】: {e}")

if __name__ == "__main__":
    # Test all currently tracked cards
    cards_to_track = [
        '730952', '722239', '141410', '325078', '395201', '657364', '128085', '100092', '100090', '93381', '91243', '91246', '93078', '91155', '776365', '115267', '98531', '724996', '186243', '455596', '328774', '776371', '704385', '91252', '663638', '107450', '91425', '704401', '730956', '107448', '91260', '520383', '91423', '120250', '93015', '91227', '721965', '91377', '674418', '618446', '128181', '455595', '585213', '704407', '744298', '230981', '289056', '91163', '164250', '607941', '618445', '618447', '657365', '186428', '128147', '128121', '128101', '396405', '93096', '131236', '408333', '128212', '663661', '607471', '91119', '459741', '91178', '91118', '185276', '601144', '105553', '91127', '253253', '601146', '606347', '106796', '104514', '91176', '104548', '91422', '91538', '390544', '127035', '93092', '149334', '180170', '128092', '132270', '132284', '91283', '387059', '128117', '146897', '132279',
        # --- Newly Added Missing Cards ---
        '502986', '91158', '488418', '128231', '162095', '105568', '91192', '91191', '103079', '91156', '124080', '135232', '332792', '326267', '469628', '141445', '671484', '156432', '126676', '292564', '292565', '674424', '199043', '489823', '485638', '505952', '407397', '106802', '116069', '418741', '160147', '103080', '111868', '454071', '518774', '128089', '671486', '475194', '332798', '705192', '100081', '104784', '134393', '671489', '545622', '103803', '105005', '392953', '98529', '641578', '671488', '135980', '91159', '103771', '124079', '671483', '141443', '141444', '470986', '396076', '601145', '91160', '91157', '98530'
    ]
    for card_id in cards_to_track:
        get_snkrdunk_trading_history(card_id, page=1, filter_psa10=True)
