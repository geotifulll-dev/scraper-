import json
import csv
import time
from curl_cffi import requests as c_req

def flatten_dict(d, parent_key='', sep='_'):
    # რთული json ბაზის CSV ცხრილში 1:1 ზე გადმოსაწყობი
    items =[]
    if not isinstance(d, dict): return {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, " / ".join([str(i) for i in v])))
        else:
            items.append((new_key, v))
    return dict(items)

def auto_find_list(node):
    # ეძებს თუ რა დაარქვეს ფარულ მონაცემებს (cars, data..).
    if isinstance(node, list): return node
    if isinstance(node, dict):
        for val in node.values():
            found = auto_find_list(val)
            if found: return found
    return[]

def main():
    print("🔥-----------------------------------------------🔥")
    print("      APP / API EXTRACTOR გაშვებულია!      ")
    print("🔥-----------------------------------------------🔥")
    
    # გაძლიერებული აპლიკაციის (App) Fake პროფილი
    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        # ვაყალბებთ App მობილური კლიენტის იმიტაციას:
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
        "Referer": "https://m.autowini.com/",
        "Origin": "https://m.autowini.com",
        "wini-code-select-country": "C0610"
    }

    all_cars_database =[]
    MAX_PAGES = 2 
    
    for page in range(1, MAX_PAGES + 1):
        target_api = f"https://v2api.autowini.com/items/cars?pageOffset={page}&pageSize=30&condition=C020"
        print(f"[\u2193] უკავშირდება Backend სერვერს: გვერდი {page}...")
        
        try:
            # ქრომის ყველაზე დაბალი შანსის დაბლოკვის მობილურის ვარიანტი: safari_ios!
            response = c_req.get(target_api, headers=HEADERS, impersonate="safari_ios", timeout=25)
            print(f"[STATUS] ސ API დაგვიბრუნა სტატუსი: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[-] DataCenter Block ჯერ კიდევ ძალაშია სტატუსით {response.status_code}! ინახება Error")
                with open(f"API_Error_{page}.html", "w", encoding="utf-8") as f:
                    f.write(response.text[:2000])
                continue
            
            data = response.json()
            extracted_list = auto_find_list(data)
            
            if extracted_list:
                print(f"[✔] გადმოიტვირთა {len(extracted_list)} სუფთა ინფორმაციის კომპონენტი!")
                for obj in extracted_list:
                    all_cars_database.append(flatten_dict(obj))
            else:
                print("[-] მონაცემების სიას ამ გვერდზე ვერ მიაგნო. ციკლი ჩერდება.")
                break
                
            time.sleep(2)
            
        except Exception as e:
            print(f"[X] მოხდა გადაჭრის პრობლემა: {e}")
            break
            
    print("------------------------------------------")
    if all_cars_database:
        # გადააქცევს სუფთა ცხრილად!
        keys = set()
        for doc in all_cars_database: keys.update(doc.keys())
        field_headers = sorted(list(keys))
        
        with open("Results_Cars.csv", "w", newline="", encoding="utf-8") as f_csv:
            w = csv.DictWriter(f_csv, fieldnames=field_headers)
            w.writeheader()
            w.writerows(all_cars_database)
        
        # ბექაფი და შენახვა ლოგების
        with open("raw_logs.json", "w", encoding="utf-8") as fb:
            json.dump(all_cars_database, fb, indent=2, default=str)
            
        print(f"[$$] ბრწყინვალეა! გადამოწმებულია და CSV შეიქმნა: {len(all_cars_database)} ჩანაწერი.")
    else:
        print("[!] შეფერხდა 403 DataCenter ბლოკირების გამო - დანარჩენ ერორები შეინახება Zip ფაილში.")

if __name__ == "__main__":
    main()
