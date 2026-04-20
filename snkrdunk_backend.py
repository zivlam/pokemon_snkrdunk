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

# 忽略 urllib3 的 OpenSSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

# 初始化 Firebase
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase 初始化成功")
except Exception as e:
    print(f"❌ Firebase 初始化失敗 (請確認是否有私鑰檔案): {e}")
    db = None

def check_dns(hostname):
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def format_to_hk_time(utc_date_str):
    if not utc_date_str or utc_date_str == '未知':
        return '未知'
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
    url = f"https://{hostname}/en/v1/products/SW---{product_id}/trading-histories"
    
    ip = check_dns(hostname)
    if not ip:
        print(f"【網路環境警示】無法解析 {hostname}。")
        return

    raw_cookies = os.environ.get('SNKRDUNK_COOKIE')
    if not raw_cookies:
        print("❌ 錯誤：找不到 Cookie，請確認您的環境變數 (SNKRDUNK_COOKIE) 是否已正確設定。")
        return

    retry_strategy = Retry(total=3, backoff_factor=2)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    headers = {
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-TW;q=0.7,zh;q=0.6',
        'cookie': raw_cookies,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
    }
    
    params = {'perPage': 10, 'page': 1, 'used': 'true'}

    try:
        print(f"正在抓取數據 (ID: {product_id})...")
        response = session.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            histories = data.get('histories') or data.get('tradingHistories')
            
            if not histories:
                print(f"【警告】ID {product_id} 找不到數據列表。")
                return

            parsed_history = []
            latest_price = 0

            # 解析最新的交易紀錄
            for item in histories:
                cond = item.get('condition') or item.get('state') or 'N/A'
                
                # 若啟用 PSA 10 篩選，非 PSA10 即跳過
                if filter_psa10 and "PSA" not in cond.upper(): 
                    continue

                raw_date = item.get('tradedAt') or item.get('createdAt') or item.get('soldAt')
                hk_time = format_to_hk_time(raw_date)
                
                # 取得價格 (原生 HKD)
                price_hkd = int(item.get('price', 0))

                # 🚀 修正點：當遇到第一筆「符合條件的 PSA10」時，就把它設為最新市價
                if len(parsed_history) == 0: 
                    latest_price = price_hkd

                parsed_history.append({
                    "id": len(parsed_history) + 1, # 確保歷史紀錄 ID 連續
                    "date": hk_time,
                    "condition": "PSA 10",
                    "priceHKD": price_hkd
                })

            if db and parsed_history:
                doc_ref = db.collection('snkrdunk_cards').document(product_id)
                doc_ref.set({
                    'id': product_id,
                    'currentPriceHKD': latest_price,
                    'history': parsed_history,
                    'lastUpdated': firestore.SERVER_TIMESTAMP
                }, merge=True) 
                
                print(f"✅ 卡片 {product_id} 資料已成功推送！最新價格: HK${latest_price}")
        else:
            print(f"❌ 錯誤：狀態碼 {response.status_code}")
            
    except Exception as e:
        print(f"【發生異常】: {e}")

if __name__ == "__main__":
    cards_to_track = ['722239', '730952', '141410']
    
    print("🚀 開始執行自動化爬蟲任務...")
    for card_id in cards_to_track:
        update_card_to_firebase(card_id)
    print("🏁 自動化任務執行完畢！")
