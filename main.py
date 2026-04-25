import json
import csv
import time
import re
from curl_cffi import requests as c_req
from bs4 import BeautifulSoup

# იყენებს ქრომის საუკეთესო 헤დერებს დამატებული 1:1 სერვერის მოთხოვნებთან
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def dict_flatten(d, parent_key='', sep='_'):
    # დაფშვნის კომპლექსურ ველებს ერთიანი ცხრილისთვის!
    items =[]
    if not isinstance(d, dict): return {parent_key: d}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(dict_flatten(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, " | ".join([str(i) for i in v if not isinstance(i, (dict, list))])))
        else:
            items.append((new_key, v))
    return dict(items)

def extract_target_car(node):
    # იდუმალი სნიფერი რომელიც 5 მეგაბაიტიანი Next_js Json-იდან საგულდაგულოდ აპარებს მხოლოდ მთავარ მანქანის ბაზას:
    if isinstance(node, dict):
        # უნიკალური ნიშნულები რაც მხოლოდ მთავარ დოკუმენტს გააჩნია..
        if "itemCd" in node and ("makerNm" in node or "makeNm" in node or "modelNm" in node):
            return node
        for val in node.values():
            result = extract_target_car(val)
            if result: return result
    elif isinstance(node, list):
        for item in node:
            result = extract_target_car(item)
            if result: return result
    return {}


def main():
    print("🔥-----------------------------------------------🔥")
    print("      DEEP CRAWLER: LISTING -> DETAIL INFO       ")
    print("🔥-----------------------------------------------🔥")

    MAX_PAGES = 2
    full_database = []
    
    # [ფაზა 1] – ყველა მანქანის გვერდის ლინკების მოძიება სერჩში:
    for page in range(1, MAX_PAGES + 1):
        list_url = f"https://www.autowini.com/search/items?itemType=cars&condition=C020&pageOffset={page}"
        print(f"\n[➡] [STEP 1] ფურცელ #{page}-ის გადამოწმება... -> {list_url}")
        
        try:
            resp = c_req.get(list_url, headers=HEADERS, impersonate="chrome120", timeout=30)
            if resp.status_code != 200:
                print(f"[-] ERROR HTTP: {resp.status_code}")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            # ლინკები (კლონების წაშლით -> set()):
            all_a_tags = soup.find_all("a", href=re.compile(r"/items/(?:Used|New)-"))
            unique_links = list(set([a.get("href") for a in all_a_tags]))
            
            if not unique_links:
                print("[-] ბმულები ვერ ვიპოვე HTML სერჩზე, გადავდივარ...")
                continue
            
            print(f"[+] აღმოჩენილია მანქანის {len(unique_links)} გვერდი, ვიწყებ სათითაოდ შესვლას (Step 2)...\n")
            
            # [ფაზა 2] – სათითაოდ ლინკზე შეცლა და ინფორმაციის კოპირება
            for index, link_endpoint in enumerate(unique_links, start=1):
                car_detail_link = "https://www.autowini.com" + link_endpoint
                print(f"    --> შევდივარ[{index}/{len(unique_links)}] : {car_detail_link}")
                
                detail_resp = c_req.get(car_detail_link, headers=HEADERS, impersonate="chrome120", timeout=30)
                if detail_resp.status_code == 200:
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                    next_script = detail_soup.find("script", id="__NEXT_DATA__")
                    
                    if next_script:
                        try:
                            car_mega_json = json.loads(next_script.string)
                            car_precise_dict = extract_target_car(car_mega_json)
                            
                            if car_precise_dict:
                                flat_item = dict_flatten(car_precise_dict)
                                flat_item["LINK_CRAWLED"] = car_detail_link # ვინახავთ წყაროს!
                                full_database.append(flat_item)
                                print(f"      [✔] წარმატება! VIN/Price/ID ამოღებულია და ცხრილში მოთავსდა!")
                            else:
                                print(f"      [?] მონაცემთა ნაკრებში `itemCd` ან `მოდელი` არ მოიძებნა!")
                                
                        except json.JSONDecodeError:
                            print(f"      [x] JSON ფორმატმა ერორი ამოაგდო.")
                    else:
                        print(f"      [x] ვერ მოიძებნა ფარული <NEXT_DATA> საწყობი.")
                        
                else:
                    print(f"      [!] მოხდა კავშირის ვარდნა! {detail_resp.status_code}")
                
                time.sleep(1)  # ბალანსი სერვერთან
                
        except Exception as big_e:
            print(f"[CRASH] ციკლის გარეთ ერორი გამოხტა! -> {big_e}")


    # [ფაზა 3] – CSV გადაბმვა და სვეტებად შედუღება!
    print("------------------------------------------")
    if full_database:
        all_columns = set()
        for d in full_database:
            all_columns.update(d.keys())
        col_list = sorted(list(all_columns))

        with open("Extracted_Mega_Database.csv", "w", newline="", encoding="utf-8-sig") as fs:
            writer = csv.DictWriter(fs, fieldnames=col_list)
            writer.writeheader()
            writer.writerows(full_database)
            
        print(f"[⭐⭐⭐] ვოა-ლა!! დასკრაპილია სულ: {len(full_database)} ინდივიდუალური ავტო-მანქანა, და აკრეფილია უამრავი სვეტი!")
    else:
        print("[!] ოპერაცია გაუქმდა მონაცემთა ცარიელობის გამო (შეიძლება დაიბლოკა ან ლინკები დაიმალა)")

if __name__ == "__main__":
    main()
