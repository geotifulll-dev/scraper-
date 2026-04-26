import json
import csv
import time
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


# 🟢 HTML დან ზუსტი სტრუქტურის ამოკითხვა შენი გამოგზავნილი მონაცემებით
def scrape_specific_html_data(soup):
    html_data = {}
    
    # 1. Main Title
    h1_title = soup.find('h1')
    if h1_title: html_data['CAR_TITLE'] = h1_title.text.strip()
    
    # 2. Photos (მხოლოდ HD და მაღალი რეზოლუციის სურათების ლინკები " | "-ით გამოყოფილი)
    photo_urls =[]
    # HTML კოდის მიხედვით "data-original-url" შეიცავს Full Res-ს!
    for img_tag in soup.find_all('a', attrs={'data-original-url': True}):
        p_url = img_tag.get('data-original-url', '')
        if p_url and p_url not in photo_urls:
            photo_urls.append(p_url)
    if photo_urls:
        html_data['GALLERY_PHOTOS_ALL'] = " | ".join(photo_urls)

    # 3. Basic Info, Size, Odometer და Condition Status 
    # ვეძებთ ნებისმიერ <dl>-ს რომელიც Basic Information და StatusReport შია
    for dl in soup.find_all('dl'):
        dt = dl.find('dt')
        dd = dl.find('dd')
        if dt and dd:
            # გავაკეთოთ ველის სახელი დიდი ასოებით Excel-სთვის (მაგ: BASIC_ODOMETER_READING)
            raw_key = dt.text.strip().replace(':', '').replace(' / ', '_').replace(' ', '_').upper()
            key_name = f"BASIC__{raw_key}"
            
            # გავფილტროთ DD-დან დახმარების ToolTip-ები რაც HTML ში იყო დამალული
            for tooltip in dd.find_all(['div', 'a', 'span'], class_=['popTip', 'btnTip']):
                tooltip.decompose() # იშლება HTML-დან ზედმეტი გაფრთხილების ტექსტები, ტოვებს რეალურ დატას (მაგ:"Not actual")
                
            # ვწმინდავთ ტექსტებს აბზაცებისგან 
            val_cleaned = ' '.join(dd.text.split())
            if val_cleaned and raw_key:
                html_data[key_name] = val_cleaned

    # 4. Featured Information (რენტა იყო? დაიტბორა? ნატაქსავებია? "YES/NO")
    featured_div = soup.find('ul', class_='special')
    if featured_div:
        for li in featured_div.find_all('li'):
            f_key_tag = li.find('span')
            f_val_tag = li.find('b')
            if f_key_tag and f_val_tag:
                key_f = "FEATURE_" + f_key_tag.text.strip().replace(' ', '_').upper().replace('/','_')
                val_f = f_val_tag.text.strip()
                html_data[key_f] = val_f

    # 5. Options (შესაძლებლობების სიის ერთ დიდ უჯრაში გადაბმა მაგალითად: Airbag | Power Seat | Sunroof ...)
    options_container = soup.find('div', class_='optionInfo')
    options_collected =[]
    if options_container:
        for opt_span in options_container.find_all('span'):
            txt = opt_span.text.strip()
            if txt: options_collected.append(txt)
            
    if options_collected:
        html_data['INTERNAL_EXTERIOR_OPTIONS'] = " | ".join(options_collected)

    # 6. Import Rules
    import_guide = soup.find('div', class_='import')
    if import_guide:
        # Import გაფრთხილებების ერთ უჯრაში შეკვრა (LHD Allowed, 6Years Age და ა.შ)
        rule_list =[sp.text.strip() for sp in import_guide.find_all(['span'])]
        html_data['IMPORT_GUIDE'] = " | ".join(rule_list)

    return html_data



def main():
    print("🔥---------------------------------------------------------🔥")
    print(" 🚀 V2-API + PRO-HTML EXTRACTOR ➜ HYBRID DEEP CRAWLER      ")
    print("🔥---------------------------------------------------------🔥")

    API_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
        "Referer": "https://m.autowini.com/",
        "Origin": "https://m.autowini.com",
        "wini-code-select-country": "C0610" 
    }

    DETAIL_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Upgrade-Insecure-Requests": "1"
    }

    # !! დააყენე სასურველი რაოდენობა !!
    MAX_PAGES = 1 
    final_dataset =[]

    for page in range(1, MAX_PAGES + 1):
        list_url = f"https://v2api.autowini.com/items/cars?pageOffset={page}&pageSize=30&condition=C020"
        print(f"\n[➡] ვაგროვებ ძირითადი სიიდან ➜ გვერდი #{page}")
        
        try:
            resp = c_req.get(list_url, headers=API_HEADERS, impersonate="safari_ios", timeout=20)
            if resp.status_code != 200: continue
            raw_cars = auto_find_list(resp.json())
            
            if not raw_cars: continue
            print(f"   [✔] ამ გვერდზე ავიღეთ {len(raw_cars)} მანქანა. მივყვები მათზე ღრმა ამოკითხვას:")

            for idx, raw_car_info in enumerate(raw_cars, 1):
                car_id = raw_car_info.get("itemCd")
                
                # ვიტოვებთ სერვერის API მონაცემებს "Backup"-ად
                combined_dict = flatten_dict(raw_car_info)
                
                if not car_id:
                    final_dataset.append(combined_dict) 
                    continue

                car_detail_link = f"https://www.autowini.com/items/Used-{car_id}"
                combined_dict["PRODUCT_LINK"] = car_detail_link
                
                print(f"[{idx}/{len(raw_cars)}] იჩხრიკება: ID-{car_id} ...", end=" ")
                
                try:
                    # ჩავალთ უშუალოდ HTML გვერდზე!
                    detail_resp = c_req.get(car_detail_link, headers=DETAIL_HEADERS, impersonate="chrome120", timeout=15)

                    if detail_resp.status_code == 200:
                        detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                        
                        # 🟢 ვაგროვებთ HTML ვიზუალურ ფოტოებს/specებს შენი 5-ივე პუნქტიდან!
                        specific_html_features = scrape_specific_html_data(detail_soup)
                        
                        # 🟢 შემდეგ ვეძებთ ასევე NEXT ფარულ JSON-ს და თუ აქვს ეგეც მოგვაქვს:
                        next_script = detail_soup.find("script", id="__NEXT_DATA__")
                        if next_script:
                            mega_json = json.loads(next_script.string)
                            exact_detail = extract_target_car(mega_json, car_id)
                            if exact_detail:
                                json_extracted = flatten_dict(exact_detail)
                                # 🟢 თუ JSON ვიპოვეთ, მთავარ combined_dict-ს ვანახლებთ:
                                combined_dict.update(json_extracted)
                        
                        # 🟢 HTML-დან აღებულ ინფორმაციას აუცილებლად ვუმატებთ ყველა სცენარში:
                        if specific_html_features:
                            combined_dict.update(specific_html_features)
                            
                        print("✅ დაასრულა.")

                    else:
                        print("⚠️ [STATUS ER]")
                
                except Exception as loop_e:
                    print("❌ [TimeOut/ER]")

                final_dataset.append(combined_dict)
                time.sleep(1) # დასვენება 1 წამი სერვერის გადატვირთვის თავიდან ასაცილებლად

        except Exception as e:
            print(f"[!] მთავარი ერორი {e}")


    print("\n------------------------------------------")
    if final_dataset:
        cols_set = set()
        for i in final_dataset:
            cols_set.update(i.keys())
        all_cols = sorted(list(cols_set)) # ვაქცევთ EXCEL/CSV ჰედერებად

        with open("Cars_Ultimate_Custom_Extracted.csv", "w", newline="", encoding="utf-8-sig") as csv_file:
            wr = csv.DictWriter(csv_file, fieldnames=all_cols, restval='')
            wr.writeheader()
            wr.writerows(final_dataset)
        print(f"🥳 პროცესი დაგვირგვინდა: {len(final_dataset)} ერთეული დეტალური ინფორმაცია ჩაწერილია 'Cars_Ultimate_Custom_Extracted.csv'-ში!")
    else:
        print("[!] ლისტი აბსოლუტურად ცარიელია.")

if __name__ == "__main__":
    main()
