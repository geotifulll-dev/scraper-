import csv
import json
import time
from curl_cffi import requests

# ის header-ები (პასპორტები) 1:1, რომლებიც შენ თვითონ გადმოიწერე ქრომის API Network-იდან. 
# ასე შენი კოდი ოფიციალურ Chrome ბრაუზერს დაემსგავსა!
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8,tr;q=0.7",
    "Origin": "https://www.autowini.com",
    "Referer": "https://www.autowini.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 OPR/129.0.0.0",
    "wini-code-select-country": "C0610",
    "Connection": "keep-alive"
}

def dict_flatten(dict_obj, separator='_', prefix=''):
    """საიდუმლო ფუნქცია: თუ API სერვერმა რთული JSON მოგვცა თავისი სუბ-კატეგორიებით 
    (მაგ: price: {base: 600, exchange: 400}), ეს კოდი აქცევს price_base და price_exchange ფორმატში, 
    რომ პირდაპირ Excel ცხრილში დაეტევეს და ინფორმაცია არ დავკარგოთ!"""
    if not isinstance(dict_obj, dict):
        return {prefix: dict_obj}
        
    flat_dictionary = {}
    for key, value in dict_obj.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        if isinstance(value, dict):
            flat_dictionary.update(dict_flatten(value, separator, new_key))
        elif isinstance(value, list):
            flat_dictionary[new_key] = str(value)
        else:
            flat_dictionary[new_key] = value
    return flat_dictionary

def search_main_list(data_chunk):
    """საიდუმლო ლოგიკა #2: ჩვენ არ ვიცით რა დაარქვეს სერვერზე 'მანქანების სიას', (Cars? Items? data?), 
    ამიტომ ეს ლოგიკა თვითონ ეძებს JSON შიგნეულობაში [List] საცავს (საიდანაც ინფორმაციაა)"""
    if isinstance(data_chunk, list) and len(data_chunk) > 0 and isinstance(data_chunk[0], dict):
        return data_chunk
    if isinstance(data_chunk, dict):
        for val in data_chunk.values():
            found = search_main_list(val)
            if found: return found
    return[]


def main():
    print("🔥===========================================🔥")
    print("API ბაზაზე (ბექ-ენდ) შეერთება წამოწყებულია!!!")
    print("🔥===========================================🔥")
    
    # ამოვიღოთ 2 გვერდის ინფორმაცია (თითო 30 მანქანაა ლინკზე მითითებული). შეიცვლება მარტივად..
    MAX_PAGES = 2 
    database =[]
    
    for current_page in range(1, MAX_PAGES + 1):
        # ეს ის ოფიციალური API საიდუმლო ლინკია რომელიც მიაგენი:
        api_link = f"https://v2api.autowini.com/items/cars?pageOffset={current_page}&pageSize=30&condition=C020"
        
        print(f"[⬇] ჩამოგვაქვს გვერდი {current_page} პირდაპირ სერვერიდან ...")
        
        try:
            # ქრომის ინდიკაცია impersonate-ით.
            req = requests.get(api_link, headers=HEADERS, impersonate="chrome120", timeout=25)
            
            if req.status_code != 200:
                print(f"[-] ვუი! API-მ სტატუსი {req.status_code} დაგვიბრუნა. ველოდებით HTML პასუხს ბექაფში.")
                with open(f"fail_page_{current_page}.html", "w", encoding="utf-8") as file:
                    file.write(req.text[:2000])
                continue
                
            raw_json = req.json()
            
            # მოდი მოვძებნოთ მანქანების სია:
            items_list = search_main_list(raw_json)
            if not items_list:
                print("[-] JSON კოდში სიას ვერ ვპოულობ!")
                continue
                
            print(f"[✔] ოპერაცია წარმატებულია! {current_page} გვერდზე ამოკითხულია {len(items_list)} დაფარული მანქანის ერთეული.")
            
            # ჩაწყობა საერთო საცავში "დაუთოვებული" ერთეულებით (Dictionary flatten):
            for itm in items_list:
                database.append(dict_flatten(itm))
                
            time.sleep(2) 
            
        except Exception as error_msg:
            print(f"[X] ვაახ შეცდომა გამოვარდა კავშირზე: {error_msg}")
            break

    print("------------------------------------------")
    if database:
        print(f"😎 გადანაცვლებულია სულ {len(database)} საუკეთესო ინფორმაცია JSON->CSV !!")
        
        # 1. ამოვწეროთ ყველა სხვადასხვა სათაური ერთობლივად სვეტების შესაქმნელად.
        cols = set()
        for c in database: cols.update(c.keys())
        all_cols = sorted(list(cols))
        
        # 2. ინახავს Csv Excel ფორმატში..
        with open("Full_Data_API_Extraction.csv", "w", newline="", encoding="utf-8") as fcsv:
            csv_writter = csv.DictWriter(fcsv, fieldnames=all_cols)
            csv_writter.writeheader()
            csv_writter.writerows(database)
            
        # 3. ვაკეთებთ აგრეთვე DataBackup-ს (მშრალ Raw-json ლოგებს ინსპექტირებისთვის)!
        with open("Raw_API_Backup.json", "w", encoding="utf-8") as fbup:
            json.dump(database, fbup, indent=4, default=str)
            
        print("📁 ამოიღეთ არტიფაქტებიდან 'Full_Data_API_Extraction.csv' გთხოვთ!")
    else:
        print("ფაილი ცარიელია! მოხდა გაუგებრობა ბლოკის ან ინფორმაციის არქონის გამო.")


if __name__ == "__main__":
    main()
