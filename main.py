import json
import csv
import time
import random  # <<-- დაემატა დროის ასარევად!
from curl_cffi import requests as c_req
from bs4 import BeautifulSoup

def flatten_dict(d, parent_key='', sep='_'):
    items =[]
    if not isinstance(d, dict): return {parent_key: d}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            str_list =[str(i) for i in v if not isinstance(i, (dict, list))]
            if str_list:
                items.append((new_key, " | ".join(str_list)))
        else:
            items.append((new_key, v))
    return dict(items)

def auto_find_list(node):
    if isinstance(node, list): return node
    if isinstance(node, dict):
        for val in node.values():
            found = auto_find_list(val)
            if found: return found
    return[]


def scrape_specific_html_data(soup):
    html_data = {}
    h1_title = soup.find('h1')
    if h1_title: html_data['CAR_TITLE'] = h1_title.text.strip()
    
    photo_urls =[]
    for img_tag in soup.find_all('a', attrs={'data-original-url': True}):
        p_url = img_tag.get('data-original-url', '')
        if p_url and p_url not in photo_urls:
            photo_urls.append(p_url)
    if photo_urls:
        html_data['GALLERY_PHOTOS_ALL'] = " | ".join(photo_urls)

    for dl in soup.find_all('dl'):
        dt = dl.find('dt')
        dd = dl.find('dd')
        if dt and dd:
            raw_key = dt.text.strip().replace(':', '').replace(' / ', '_').replace(' ', '_').upper()
            key_name = f"BASIC__{raw_key}"
            for tooltip in dd.find_all(['div', 'a', 'span'], class_=['popTip', 'btnTip']):
                tooltip.decompose()
            val_cleaned = ' '.join(dd.text.split())
            if val_cleaned and raw_key:
                html_data[key_name] = val_cleaned

    featured_div = soup.find('ul', class_='special')
    if featured_div:
        for li in featured_div.find_all('li'):
            f_key_tag = li.find('span')
            f_val_tag = li.find('b')
            if f_key_tag and f_val_tag:
                key_f = "FEATURE_" + f_key_tag.text.strip().replace(' ', '_').upper().replace('/','_')
                val_f = f_val_tag.text.strip()
                html_data[key_f] = val_f

    options_container = soup.find('div', class_='optionInfo')
    options_collected =[]
    if options_container:
        for opt_span in options_container.find_all('span'):
            txt = opt_span.text.strip()
            if txt: options_collected.append(txt)
    if options_collected:
        html_data['INTERNAL_EXTERIOR_OPTIONS'] = " | ".join(options_collected)

    import_guide = soup.find('div', class_='import')
    if import_guide:
        rule_list =[sp.text.strip() for sp in import_guide.find_all(['span'])]
        html_data['IMPORT_GUIDE'] = " | ".join(rule_list)

    return html_data

def main():
    print("🔥---------------------------------------------------------🔥")
    print(" 🚀 V2-API + PRO-HTML EXTRACTOR + ANTI-BAN CRAWLER 🛡️")
    print("🔥---------------------------------------------------------🔥")

    API_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36"
    }

    DETAIL_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Upgrade-Insecure-Requests": "1",
        "Accept-Encoding": "gzip, deflate, br",
    }

    # 🟢 [ᲐᲮᲐᲚᲘ]: სესიის მენეჯერი ინარჩუნებს Cookie-ებს 1 ძებნაზე ისე როგორც ბრაუზერში
    detail_session = c_req.Session(impersonate="chrome120", headers=DETAIL_HEADERS)

    MAX_PAGES = 1 
    final_dataset =[]

    for page in range(1, MAX_PAGES + 1):
        list_url = f"https://v2api.autowini.com/items/cars?pageOffset={page}&pageSize=30&condition=C020"
        print(f"\n[➡] ვაგროვებ ძირითადი სიიდან ➜ გვერდი #{page}")
        
        try:
            # Main API ირევა ნაკლებად
            resp = c_req.get(list_url, headers=API_HEADERS, impersonate="safari_ios", timeout=20)
            if resp.status_code != 200: continue
            raw_cars = auto_find_list(resp.json())
            
            if not raw_cars: continue
            print(f"   [✔] ამ გვერდზე აღმოჩნდა {len(raw_cars)} მანქანა. ვიწყებ შიდა გვერდების დასკანერებას:")

            for idx, raw_car_info in enumerate(raw_cars, 1):
                detail_path = raw_car_info.get("detailUrl", "")
                item_cd = raw_car_info.get("listingId", "NoID")

                combined_dict = flatten_dict(raw_car_info)
                if not detail_path:
                    final_dataset.append(combined_dict) 
                    continue

                car_detail_link = f"https://www.autowini.com{detail_path}"
                combined_dict["PRODUCT_LINK"] = car_detail_link
                
                print(f"[{idx}/{len(raw_cars)}] იჩხრიკება: {item_cd} ...", end=" ", flush=True)
                
                # 🟢 403 ერორის Retries Logic (ცდის მაქსიმუმ 3-ჯერ თითო მანქანაზე)
                html_found = False
                max_retries = 3

                for attempt in range(max_retries):
                    try:
                        detail_resp = detail_session.get(car_detail_link, timeout=15)

                        if detail_resp.status_code == 200:
                            detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                            specific_html_features = scrape_specific_html_data(detail_soup)
                            
                            if specific_html_features:
                                combined_dict.update(specific_html_features)
                                html_found = True
                            break # წამოიღო მონაცემი წამატებით -> გამოვიდეთ მცდელობების (attempt) ციკლიდან
                            
                        elif detail_resp.status_code == 403:
                            # 🛡️ დაიჭირა სისტემამ AntiBot! ვეუბნებით რომ 15 წამი შეიკავოს თავი ახალ მოთხოვნამდე 
                            print(f"\n   [!] 403 Bot-დაცვა ამოქმედდა! დასვენება 15 წამი (მცდელობა {attempt+1}/3)...")
                            time.sleep(15) 
                        else:
                            break # თუ სხვა ერორია (მაგ. 404 ან 500) პირდაპირ ჩავხსნათ ამაზე მცდელობები 
                    except Exception as loop_e:
                        print(f"   [-] Timeout..", end="")
                        time.sleep(3) # თაიმაუტზე პატარა 3-წამიანი დალოდება

                if html_found:
                    print("✅ HTML დაემატა.")
                else:
                    print("⚠ დაზღვევის ბაზით შენარჩუნდა.")
                    
                final_dataset.append(combined_dict)
                
                # 🟢 [ᲛᲗᲐᲕᲐᲠᲘ ᲪᲕᲚᲘᲚᲔᲑᲐ]: Random delay მუდმივ 1-წამის მაგივრად (1.5 წმ -დან 3.5-მდე სუფთა დიაპაზონით)! 
                # სისტემა ვერ აღიქვამს როგორც მკაცრად დაპროგრამებულ სკრიპტს!
                random_wait = random.uniform(1.5, 3.5)
                time.sleep(random_wait)

        except Exception as e:
            print(f"[!] მთავარი გვერდის ერორი {e}")


    print("\n------------------------------------------")
    if final_dataset:
        cols_set = set()
        for i in final_dataset:
            cols_set.update(i.keys())
        all_cols = sorted(list(cols_set))

        with open("Cars_Ultimate_Data_Scraped.csv", "w", newline="", encoding="utf-8-sig") as csv_file:
            wr = csv.DictWriter(csv_file, fieldnames=all_cols, restval='')
            wr.writeheader()
            wr.writerows(final_dataset)
        print(f"🥳 პროცესი დასრულდა! მყარად ჩაწერილია Excel/CSV: {len(final_dataset)}")
    else:
        print("[!] სია ცარიელია.")

if __name__ == "__main__":
    main()
