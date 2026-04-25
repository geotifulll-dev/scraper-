import requests
import csv
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.autowini.com/search/items?itemType=cars&condition=C020",
}

BASE_URL = "https://www.autowini.com"


def try_api():
    """API endpoint-ების ცდა"""
    
    # შესაძლო API endpoints
    api_urls = [
        "https://www.autowini.com/api/v2/search/items?itemType=cars&condition=C020&pageOffset=1&pageSize=40",
        "https://www.autowini.com/api/search/items?itemType=cars&condition=C020&pageOffset=1",
        "https://api.autowini.com/v2/search/items?itemType=cars&condition=C020",
    ]
    
    for url in api_urls:
        print(f"🔍 Trying: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ API works! Status: {resp.status_code}")
                return data
        except Exception as e:
            print(f"   ❌ {e}")
    return None


def try_html_parse():
    """HTML-დან ჩაშენებული JSON-ის ამოღება"""
    url = "https://www.autowini.com/search/items?itemType=cars&condition=C020"
    print(f"\n📄 Fetching HTML: {url}")
    
    resp = requests.get(url, headers=HEADERS, timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   HTML length: {len(resp.text)}")
    
    html = resp.text
    
    # __NEXT_DATA__ ან სხვა script tags
    patterns = [
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
        r'window\.__DATA__\s*=\s*({.*?});',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            print(f"✅ Found embedded data with pattern!")
            try:
                data = json.loads(match.group(1))
                return data
            except:
                print("   ⚠️ Could not parse JSON")
    
    # Debug: პირველი 2000 სიმბოლო
    print("\n--- HTML Preview (first 2000 chars) ---")
    print(html[:2000])
    print("--- End Preview ---\n")
    
    return None


def parse_api_data(data):
    """API response-დან მანქანების ამოღება"""
    cars = []
    
    # სხვადასხვა JSON structure-ის ცდა
    items = []
    
    if isinstance(data, dict):
        # შესაძლო keys
        for key in ["items", "data", "result", "results", "content", "list", "carList"]:
            if key in data:
                items = data[key]
                print(f"📦 Found items in key: '{key}' ({len(items)} items)")
                break
        
        # nested
        if not items and "data" in data and isinstance(data["data"], dict):
            for key in ["items", "list", "results"]:
                if key in data["data"]:
                    items = data["data"][key]
                    print(f"📦 Found items in data.{key} ({len(items)} items)")
                    break
    
    if not items:
        print("⚠️ Could not find items in response")
        print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        return []
    
    for item in items:
        car = {
            "title": "",
            "price_usd": "",
            "details": "",
            "location": "",
            "url": "",
            "image": "",
            "year": "",
            "mileage": "",
        }
        
        # ყველა key-ს ვამოწმებ
        if isinstance(item, dict):
            # title
            for k in ["title", "itemName", "name", "itemNm", "goodsNm"]:
                if k in item and item[k]:
                    car["title"] = str(item[k])
                    break
            
            # price
            for k in ["price", "exchangePrice", "exchangedPrice", "itemPrice", "amt"]:
                if k in item and item[k]:
                    car["price_usd"] = str(item[k])
                    break
            
            # url
            for k in ["itemUrl", "url", "detailUrl", "link"]:
                if k in item and item[k]:
                    car["url"] = str(item[k])
                    break
            
            # image
            for k in ["thumbnail", "thumbnailUrl", "imageUrl", "imgUrl", "img"]:
                if k in item and item[k]:
                    car["image"] = str(item[k])
                    break
            
            # year
            for k in ["year", "modelYear", "yearNm"]:
                if k in item and item[k]:
                    car["year"] = str(item[k])
                    break
            
            # mileage
            for k in ["mileage", "mile", "mileageKm"]:
                if k in item and item[k]:
                    car["mileage"] = str(item[k])
                    break
            
            # details
            for k in ["description", "summary", "itemDesc"]:
                if k in item and item[k]:
                    car["details"] = str(item[k])[:200]
                    break
            
            # თუ URL არ აქვს, construct
            if not car["url"] and "itemId" in item:
                car["url"] = f"{BASE_URL}/items/{item['itemId']}"
            
            # ყველა key debug-ისთვის
            print(f"   🔑 Keys: {list(item.keys())[:10]}")
        
        cars.append(car)
    
    return cars


def save_csv(cars, filename="autowini_cars.csv"):
    """CSV-ში შენახვა"""
    if not cars:
        print("❌ No cars to save")
        return
    
    fieldnames = list(cars[0].keys())
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cars)
    
    print(f"\n🎉 Saved {len(cars)} cars to {filename}")


def main():
    print("=" * 50)
    print("🚗 AutoWin Scraper")
    print("=" * 50)
    
    # მეთოდი 1: API
    print("\n--- Method 1: API ---")
    api_data = try_api()
    if api_data:
        cars = parse_api_data(api_data)
        if cars:
            save_csv(cars)
            return
    
    # მეთოდი 2: HTML parsing
    print("\n--- Method 2: HTML Parse ---")
    html_data = try_html_parse()
    if html_data:
        cars = parse_api_data(html_data)
        if cars:
            save_csv(cars)
            return
    
    # Debug output
    print("\n❌ Could not extract car data")
    print("💡 Debug info saved for analysis")


if __name__ == "__main__":
    main()
