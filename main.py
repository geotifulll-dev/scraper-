import json
import csv
import time
from curl_cffi import requests as c_req
from bs4 import BeautifulSoup

def flatten_dict(d, parent_key='', sep='_'):
    # რთული API/NEXT ველების ჩაშლა excel-ისთვის
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
    # პოულობს მანქანების Array სიას
    if isinstance(node, list): return node
    if isinstance(node, dict):
        for val in node.values():
            found = auto_find_list(val)
            if found: return found
    return[]

def extract_target_car(node, target_id):
    if isinstance(node, dict):
        if node.get("itemCd") == target_id:
            return node
        for val in node.values():
            result = extract_target_car(val, target_id)
            if result: return result
    elif isinstance(node, list):
        for item in node:
            result = extract_target_car(item, target_id)
            if result: return result
    return {}

# 🟢 [ᲐᲮᲐᲚᲘ ᲤᲣᲜᲥᲪᲘᲐ]: პირდაპირ HTML ტეგებიდან მონაცემების ამოკითხვა პროდუქტის გვერდზე
def scrape_visible_html_data(soup):
    html_data = {}
    
    # 1. ძირითადი Title და ფარული OpenGraph ტეგები (სურათი, ფასი)
    title_tag = soup.find('title')
    if title_tag: html_data['PAGE_TITLE'] = title_tag.text.strip()
    
    og_img = soup.find('meta', property='og:image')
    if og_img: html_data['MAIN_IMAGE'] = og_img.get('content', '')

    meta_price = soup.find('meta', property='product:price:amount')
    if meta_price: html_data['META_PRICE'] = meta_price.get('content', '')

    # 2. ვიპოვოთ H1 (სავარაუდოდ მანქანის მთავარი დასახელება)
    h1 = soup.find('h1')
    if h1: html_data['HTML_H1_HEADING'] = h1.text.strip()
    
    # 3. დინამიურად ამოვიღოთ მონაცემები <dl>/<dt>/<dd> ტეგებიდან (თუ არის HTML-ში)
    for dl in soup.find_all('dl'):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            key = dt.text.strip().replace(":", "").upper().replace(" ", "_")
            val = dd.text.strip()
            if key and val:
                html_data[f"SPEC_DOM_{key}"] = val

    # 4. ამოვიღოთ ცხრილის <tr>/<th>/<td> მონაცემები სპეციფიკაციებიდან
    for tr in soup.find_all('tr'):
        th = tr.find('th')
        td = tr.find('td')
        if th and td:
            key = th.text.strip().replace(":", "").upper().replace(" ", "_")
            val = td.text.strip()
            if key and val:
                html_data[f"TABLE_DOM_{key}"] = val
                
    return html_data


def main():
    print("🔥---------------------------------------------------------🔥")
    print(" 🚀 V2-API + HTML SCRAPE ➜ HYBRID CRAWLER: LIST -> DETAIL ")
    print("🔥---------------------------------------------------------🔥")

    API_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
        "Referer": "https://m.autowini.com/",
        "Origin": "https://m.autowini.com",
        "wini-code-select-country": "C0610" # Country Code for example (Georgia)
    }

    DETAIL_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Upgrade-Insecure-Requests": "1"
    }

    MAX_PAGES = 2 
    final_dataset =[]

    # [STEP 1] -> გვერდების ამოკითხვა სერვერული V2API საშუალებით
    for page in range(1, MAX_PAGES + 1):
        list_url = f"https://v2api.autowini.com/items/cars?pageOffset={page}&pageSize=30&condition=C020"
        print(f"\n[➡][STEP 1] ვეცნობი მთავარი V2API-ს სიას - ფურცელი #{page}")
        
        try:
            resp = c_req.get(list_url, headers=API_HEADERS, impersonate="safari_ios", timeout=20)
            if resp.status_code != 200:
                print(f"[-] DataCenter-მა API კავშირიც დაბლოკა (Status {resp.status_code}).")
                continue

            raw_cars = auto_find_list(resp.json())
            
            if not raw_cars:
                print(f"[-] ამ API გვერდზე ლისტი ცარიელია.")
                continue

            print(f"[✔] აღმოჩენილია {len(raw_cars)} ობიექტი! ➜ იწყება HTML და დეტალური სკრაპინგი სათითაოდ:")

            #[STEP 2] სათითაოდ გავლის ციკლი ნაპოვნ ID-ებზე:
            for idx, raw_car_info in enumerate(raw_cars, 1):
                car_id = raw_car_info.get("itemCd")
                
                base_flatten = flatten_dict(raw_car_info)
                if not car_id:
                    final_dataset.append(base_flatten) 
                    continue

                car_detail_link = f"https://www.autowini.com/items/Used-{car_id}"
                print(f"    --> იჩხრიკება [{idx}/{len(raw_cars)}] : ID-{car_id}")
                
                try:
                    # ფარულად ჩაძვრომა კონკრეტული ავტომობილის დეტალების ტექსტებში
                    detail_resp = c_req.get(car_detail_link, headers=DETAIL_HEADERS, impersonate="chrome120", timeout=15)
                    deep_info_found = False
                    visual_html_data = {} # შესანახი ცარიელი ობიექტი ვიზუალური დატასთვის

                    if detail_resp.status_code == 200:
                        detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                        
                        # 🟢 ვაგროვებთ HTML/პროდუქტის გვერდზე ხილულ დატას (ჩვენი ახალი ფუნქცია)
                        visual_html_data = scrape_visible_html_data(detail_soup)

                        next_script = detail_soup.find("script", id="__NEXT_DATA__")
                        
                        # თუ არის ფარული მეგა JSON - ჯერ ამას ვიღებთ და მერე ვუმატებთ ვიზუალურ (HTML) დატას.
                        if next_script:
                            mega_json = json.loads(next_script.string)
                            exact_detail = extract_target_car(mega_json, car_id)
                            
                            if exact_detail:
                                rich_car = flatten_dict(exact_detail)
                                rich_car["LINK"] = car_detail_link
                                
                                # ვაერთიანებთ NextJSON და HTML მონაცემებს 
                                rich_car.update(visual_html_data) 
                                
                                final_dataset.append(rich_car)
                                print(f"      [⭐⭐⭐] წარმატება! სრულყოფილი NEXT-JSON & HTML მონაცემი გაერთიანდა!")
                                deep_info_found = True

                    # ----------------- FAIL-SAFE LOGIC --------------------
                    if not deep_info_found:
                        print(f"      [~] NEXT-JSON ვერ ვიპოვე. ავიღე API-ს ბაზა + HTML Scraping.")
                        base_flatten["LINK"] = car_detail_link
                        
                        # მაინც ვუმატებთ იმას რაც HTML ტეგებიდან მოვქექეთ
                        if visual_html_data:
                            base_flatten.update(visual_html_data) 
                            
                        final_dataset.append(base_flatten)

                except Exception as loop_e:
                    print(f"[x] Timeout/ერორი მანქანაზე. ვიყენებ მხოლოდ API-ს. - {loop_e}")
                    base_flatten["LINK"] = f"https://www.autowini.com/items/Used-{car_id}"
                    final_dataset.append(base_flatten)

                time.sleep(1)  

        except Exception as api_err:
            print(f"[!] მთავარი გვერდის API ERROR: {api_err}")


    # [STEP 3] მონაცემების შენახვა CSV-ში
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
        print(f"[#] სრული პროცესი დასრულდა! HTML დატაც ჩაიტვირთა. ჩაწერილია: {len(final_dataset)} ერთეული.")
    else:
        print("[!] ლისტი აბსოლუტურად ცარიელია.")


if __name__ == "__main__":
    main()
