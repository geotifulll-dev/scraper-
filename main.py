import csv
import time
import re
from bs4 import BeautifulSoup
# !! requests ბიბლიოთეკას ვცვლით სპეციალური chrome ბიბლიოთეკით
from curl_cffi import requests

def get_page_url(page):
    if page == 1:
        return "https://www.autowini.com/search/items?itemType=cars&condition=C020"
    return f"https://www.autowini.com/search/items?itemType=cars&condition=C020&pageOffset={page}"

def extract_cars_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    cars =[]
    
    links = soup.find_all("a", href=re.compile(r"/items/Used-"))
    for link in links:
        car = {}
        car["url"] = "https://www.autowini.com" + link.get("href", "")
        
        h3 = link.find("h3")
        if h3:
            n_span = h3.find("span")
            if n_span:
                n_span.decompose()
            car["title"] = h3.get_text(strip=True)
        else:
            car["title"] = "N/A"
            
        p = link.find("p")
        car["details"] = p.get_text(strip=True) if p else "N/A"
        
        price = link.find("exchanged-price")
        car["price"] = price.get("price", "N/A") if price else "N/A"
        
        flag = link.find("img", alt="flag")
        if flag and flag.find_next_sibling("span"):
            car["location"] = flag.find_next_sibling("span").get_text(strip=True)
        else:
            car["location"] = "N/A"
            
        wish_btn = link.find("button", attrs={"aria-label": "Add to wishlist button"})
        if wish_btn and wish_btn.find_next_sibling("span"):
            car["wishlist"] = wish_btn.find_next_sibling("span").get_text(strip=True)
        else:
            car["wishlist"] = "0"
            
        mk_icon = link.find("img", alt="mk_faster")
        if mk_icon:
            extra_div = mk_icon.find_next_sibling("div")
            if extra_div:
                features =[span.get_text(strip=True) for span in extra_div.find_all("span") if span.get_text(strip=True)]
                car["features"] = " / ".join(features)
            else:
                car["features"] = "N/A"
        else:
            car["features"] = "N/A"
            
        cars.append(car)
        
    return cars

def save_to_csv(cars, filename="results.csv"):
    if not cars:
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cars[0].keys())
        writer.writeheader()
        writer.writerows(cars)
    print(f"✅ წამოიღო და ჩაიწერა სულ: {len(cars)} მანქანა.")

def main():
    print("🔥" * 20)
    print("!!! ეშვება BYPASS-VER-02 ბოლო მეთოდი ქრომის ემულატორით !!!")
    print("🔥" * 20)
    
    MAX_PAGES = 2 
    all_extracted_cars =[]
    
    for page in range(1, MAX_PAGES + 1):
        target_url = get_page_url(page)
        print(f"[\u2193] ვამოწმებ გვერდს #{page}...")
        
        try:
            # მთავარი მომენტი (ანტი-ბოტ საწინააღმდეგო იმპერსონაცია Chrome ვერსია 120-ის იმიტირებით)
            resp = requests.get(target_url, impersonate="chrome120", timeout=30)
            
            if resp.status_code != 200:
                print(f"[-] საიტმა კვლავ დაბლოკა, დააბრუნა კოდი: {resp.status_code}")
                with open("debug_html.txt", "w", encoding="utf-8") as f:
                    f.write(resp.text[:5000])
                break
                
            page_cars = extract_cars_from_html(resp.text)
            print(f"[+] გვერდზე იპოვნა: {len(page_cars)} ცალი მანქანა")
            
            if not page_cars:
                with open("debug_html.txt", "w", encoding="utf-8") as f:
                    f.write(resp.text[:5000])
                break
                
            all_extracted_cars.extend(page_cars)
            time.sleep(3) 
            
        except Exception as e:
            print(f"[!] შეცდომა: {e}")
            break

    print("=" * 50)
    if all_extracted_cars:
        print(f"[#] მისია შესრულებულია! სრული რაოდენობა: {len(all_extracted_cars)} ჩანაწერი.")
        save_to_csv(all_extracted_cars, "results.csv")
    else:
        print("ინფორმაცია ვერსაიდან ვერ მოგროვდა.")

if __name__ == "__main__":
    main()
