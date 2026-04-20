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

# 初始化 Firebase (請確保執行環境中有 'serviceAccountKey.json'，GitHub Actions 會自動生成它)
try:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase 初始化成功")
except Exception as e:
    print(f"❌ Firebase 初始化失敗 (請確認是否有私鑰檔案): {e}")
    db = None

def check_dns(hostname):
    """診斷 DNS 解析狀態"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None

def format_to_hk_time(utc_date_str):
    """將 UTC 時間字串轉換為香港時間 (UTC+8)"""
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
    """
    獲取 SNKRDUNK 數據並將結果推送到 Firebase
    """
    hostname = "snkrdunk.com"
    url = f"https://{hostname}/en/v1/products/SW---{product_id}/trading-histories"
    
    # 1. 網路與 DNS 預檢
    ip = check_dns(hostname)
    if not ip:
        print(f"【網路環境警示】無法解析 {hostname}。")
        return

    # 🌟 安全機制：從 GitHub Secrets (環境變數) 讀取 Cookie，絕對不要寫死在程式碼中！
    raw_cookies = os.environ.get('SNKRDUNK_COOKIE')
    
    if not raw_cookies:
        print("❌ 錯誤：找不到 Cookie，請確認您的環境變數 (SNKRDUNK_COOKIE) 是否已正確設定。")
        return

    # 設定網路請求自動重試機制
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
            for index, item in enumerate(histories):
                cond = item.get('condition') or item.get('state') or 'N/A'
                
                # 如果啟用了 PSA 10 篩選，則跳過不符合的資料
                if filter_psa10 and "PSA" not in cond.upper(): 
                    continue

                raw_date = item.get('tradedAt') or item.get('createdAt') or item.get('soldAt')
                hk_time = format_to_hk_time(raw_date)
                
                # 取得價格 (原始數據已是 HKD，直接轉為整數即可)
                price_hkd = int(item.get('price', 0))

                # 記錄最新的一筆價格作為當前市價
                if index == 0: 
                    latest_price = price_hkd

                parsed_history.append({
                    "id": index + 1,
                    "date": hk_time,
                    "condition": "PSA 10",
                    "priceHKD": price_hkd
                })

            # 將結果寫入 Firebase Firestore
            if db and parsed_history:
                doc_ref = db.collection('snkrdunk_cards').document(product_id)
                # 使用 merge=True，這樣只會更新價格與歷史，不會洗掉您在前端定義的卡片名稱、圖片等靜態欄位
                doc_ref.set({
                    'id': product_id,
                    'currentPriceHKD': latest_price,
                    'history': parsed_history,
                    'lastUpdated': firestore.SERVER_TIMESTAMP
                }, merge=True) 
                
                print(f"✅ 卡片 {product_id} 資料已成功推送至 Firebase! 最新價格: HK${latest_price}")
        else:
            print(f"❌ 錯誤：狀態碼 {response.status_code}")
            
    except Exception as e:
        print(f"【發生異常】: {e}")

if __name__ == "__main__":
    # 您要自動追蹤的卡片清單 (Mega 噴火龍 X, MEGA 耿鬼, 25週年皮卡丘)
    cards_to_track = ['722239', '730952', '141410']
    
    print("🚀 開始執行自動化爬蟲任務...")
    for card_id in cards_to_track:
        update_card_to_firebase(card_id)
    print("🏁 自動化任務執行完畢！")
