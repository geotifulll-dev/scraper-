import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.autowini.com"
SEARCH_URL = "https://www.autowini.com/search/items?itemType=cars&condition=C020"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def scrape_page(page_num):
    """ერთი გვერდის scrape"""
    url = f"{SEARCH_URL}&pageOffset={page_num}"
    print(f"📄 Scraping page {page_num}: {url}")
    
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"❌ Error: Status {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # მანქანების ლინკების პოვნა
    car_links = soup.find_all("a", href=True)
    cars = []
    
    for link in car_links:
        href = link.get("href", "")
        if not href.startswith("/items/Used-"):
            continue
        
        car = {}
        
        # ლინკი
        car["url"] = BASE_URL + href
        
        # სათაური (h3)
        h3 = link.find("h3")
        if h3:
            # N ნიშნის გარეშე
            title_text = h3.get_text(strip=True)
            car["title"] = title_text.replace("N", "").strip()
        else:
            car["title"] = "N/A"
        
        # დეტალები (p tag ინფო მისამართით)
        p_tag = link.find("p")
        if p_tag:
            car["details"] = p_tag.get_text(strip=True)
        else:
            car["details"] = "N/A"
        
        # ფასი (exchanged-price)
        price_el = link.find("exchanged-price")
        if price_el:
            car["price_usd"] = price_el.get("price", "N/A")
        else:
            # alt: სხვა ფასის პოვნა
            price_div = link.find("div", class_="css-19fxa0g")
            if price_div:
                car["price_usd"] = price_div.get_text(strip=True).replace("$", "").strip()
            else:
                car["price_usd"] = "N/A"
        
        # სურათი
        img = link.find("img", class_="css-k7hb9y")
        if img:
            car["image"] = img.get("src", "N/A")
        else:
            car["image"] = "N/A"
        
        # ადგილმდებარეობა
        location_span = link.find("span", string=lambda t: t and ("Korea" in t or "Japan" in t or "UAE" in t) if t else False)
        if location_span:
            car["location"] = location_span.get_text(strip=True)
        else:
            car["location"] = "N/A"
        
        # Wishlist count
        wish = link.find("span", class_="css-13xkcs5")
        if wish:
            car["wishlist"] = wish.get_text(strip=True)
        else:
            car["wishlist"] = "0"
        
        cars.append(car)
    
    print(f"   ✅ Found {len(cars)} cars")
    return cars


def main():
    all_cars = []
    
    # რამდენი გვერდი გინდა scrape
    PAGES = 3  # შეცვალე რამდენიც გინდა
    
    for page in range(1, PAGES + 1):
        cars = scrape_page(page)
        all_cars.extend(cars)
        time.sleep(2)  # rate limit-ის თავიდან აცილება
    
    # CSV-ში შენახვა
    if all_cars:
        filename = "autowini_cars.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "price_usd", "details", "location", "url", "image", "wishlist"])
            writer.writeheader()
            writer.writerows(all_cars)
        
        print(f"\n🎉 Done! {len(all_cars)} cars saved to {filename}")
    else:
        print("\n❌ No cars found!")


if __name__ == "__main__":
    main()
