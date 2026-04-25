import requests
import csv
import time
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ეს ფუნქცია არეგულირებს, პირველ გვერდზე შევიდეს თუ მომდევნოზე (pageOffset)
def get_page_url(page):
    if page == 1:
        return "https://www.autowini.com/search/items?itemType=cars&condition=C020"
    return f"https://www.autowini.com/search/items?itemType=cars&condition=C020&pageOffset={page}"

def extract_cars_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    cars =[]
    
    # ვეძებთ ყველა სავარაუდო მანქანის ბმულს (მათ ყოველთვის /items/Used- ით იწყებენ)
    links = soup.find_all("a", href=re.compile(r"/items/Used-"))
    
    for link in links:
        car = {}
        
        # 1. URL
        car["url"] = "https://www.autowini.com" + link.get("href", "")
        
        # 2. Title (ახალი ტეგის 'N' -ის უსაფრთხოდ ამოჭრა სათაურიდან)
        h3 = link.find("h3")
        if h3:
            n_span = h3.find("span") # აშორებს 'N' ახალ ნიშანს
            if n_span: 
                n_span.decompose()
            car["title"] = h3.get_text(strip=True)
        else:
            car["title"] = "N/A"
            
        # 3. Details (ID, ძრავა, და ა.შ)
        p = link.find("p")
        car["details"] = p.get_text(strip=True) if p else "N/A"
        
        # 4. Price 
        price = link.find("exchanged-price")
        car["price"] = price.get("price", "N/A") if price else "N/A"
        
        # 5. Location (ვეძებთ დროშის ლოგოს და შემდეგ ამოგვაქვს ტექსტი S.Korea ან ა.შ)
        flag = link.find("img", alt="flag")
        if flag and flag.find_next_sibling("span"):
            car["location"] = flag.find_next_sibling("span").get_text(strip=True)
        else:
            car["location"] = "N/A"
            
        # 6. Wishlist Count (მოთხოვნილი კონკრეტული სტრუქტურის მიხედვით ვიღებთ Aria label-დან)
        wish_btn = link.find("button", attrs={"aria-label": "Add to wishlist button"})
        if wish_btn and wish_btn.find_next_sibling("span"):
            car["wishlist"] = wish_btn.find_next_sibling("span").get_text(strip=True)
        else:
            car["wishlist"] = "0"
            
        # 7. Extras/Features (ამოვიღოთ Smart key, Navi, etc.. mk_faster იკონიდან მოყოლებული)
        mk_icon = link.find("img", alt="mk_faster")
        if mk_icon:
            # ამოვიღოთ ისეთი ელემენტები როგორებიცაა Smart key, One-owner
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
        # csv ველები იქნება ლექსიკონის key-ების მიხედვით
        writer = csv.DictWriter(f, fieldnames=cars[0].keys())
        writer.writeheader()
        writer.writerows(cars)
    print(f"==> წარმატებით შეინახა {len(cars)} ჩანაწერი -> {filename}-ში.")

def main():
    print("=" * 50)
    print("AutoWin Scraper: მრავალი გვერდის ამოღება იწყება!")
    print("=" * 50)
    
    # აი აქ შეგიძლიათ დააყენოთ რამდენი გვერდი დასკრაპოს, ამ შემთხვევაში გავაკეთოთ 2.
    MAX_PAGES = 2 
    all_extracted_cars =[]
    
    for page in range(1, MAX_PAGES + 1):
        target_url = get_page_url(page)
        print(f"[\u2193] ვამოწმებ გვერდს #{page}: {target_url}")
        
        try:
            resp = requests.get(target_url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"[-] ვებ-საიტმა შეზღუდა კავშირი Status Code-ით: {resp.status_code}")
                break
                
            # Html ამოღების ლოგიკის ჩართვა
            page_cars = extract_cars_from_html(resp.text)
            print(f"[+] გვერდზე {page} ნაპოვნია მანქანების რაოდენობა: {len(page_cars)}")
            
            if not page_cars:
                print(f"[-] ამ გვერდზე ინფორმაცია აღარ არის, ციკლი სრულდება.")
                break
                
            # საერთო ბაზაში დამატება
            all_extracted_cars.extend(page_cars)
            time.sleep(2) # სერვერს რომ არ გავუბრაზოთ, ვასვენებთ 2 წამი გვერდიდან-გვერდზე
            
        except Exception as e:
            print(f"[!] შეცდომა სკრაპინგისას გვერდზე {page}: {e}")
            break

    print("=" * 50)
    if all_extracted_cars:
        print(f"[#] სრულად დასკრაპილია {len(all_extracted_cars)} უნიკალური ჩანაწერი.")
        save_to_csv(all_extracted_cars, "results.csv")
    else:
        print("მონაცემები ვერ მოიძებნა. დაასრულა.")

if __name__ == "__main__":
    main()
