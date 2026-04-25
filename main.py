import requests
import csv
import json
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_html():
    url = "https://www.autowini.com/search/items?itemType=cars&condition=C020"
    print(f"Fetching: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
        return resp.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return ""

def extract_next_data(html):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        print("Found __NEXT_DATA__!")
        return json.loads(match.group(1))
    return None

def extract_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    cars =[]
    links = soup.find_all("a", href=re.compile(r"/items/Used-"))
    print(f"Found {len(links)} car links")
    
    for link in links:
        car = {}
        car["url"] = "https://www.autowini.com" + link.get("href", "")
        h3 = link.find("h3")
        car["title"] = h3.get_text(strip=True) if h3 else "N/A"
        p = link.find("p")
        car["details"] = p.get_text(strip=True) if p else "N/A"
        price = link.find("exchanged-price")
        car["price"] = price.get("price", "N/A") if price else "N/A"
        loc = link.find("span", string=re.compile(r"Korea|Japan|UAE|China"))
        car["location"] = loc.get_text(strip=True) if loc else "N/A"
        wish = link.find("span", class_=re.compile(r"css-13xkcs5"))
        car["wishlist"] = wish.get_text(strip=True) if wish else "0"
        cars.append(car)
    return cars

def save_csv(cars, filename="results.csv"):
    if not cars:
        print("No cars found!")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cars[0].keys())
        writer.writeheader()
        writer.writerows(cars)
    print(f"Saved {len(cars)} cars to {filename}")

def main():
    print("=" * 50)
    print("AutoWin Scraper Starting...")
    print("=" * 50)
    
    html = fetch_html()
    
    if not html:
        print("Failed to get HTML content.")
        return
    
    data = extract_next_data(html)
    if data:
        with open("debug_data.json", "w") as f:
            json.dump(data, f, indent=2, default=str)
        print("Saved debug_data.json")
    
    cars = extract_from_html(html)
    if cars:
        print(f"First car found: {cars[0]['title']} - {cars[0]['price']}")
        save_csv(cars)
    else:
        print("No cars in HTML. Check debug_html.txt")
        with open("debug_html.txt", "w") as f:
            f.write(html[:5000])
    
    print("Scraping Completed!")

if __name__ == "__main__":
    main()
