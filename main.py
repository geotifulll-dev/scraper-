import requests
from bs4 import BeautifulSoup

def scrape(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    titles = soup.find_all("h2")

    for i, title in enumerate(titles, 1):
        print(f"{i}. {title.text.strip()}")

if __name__ == "__main__":
    scrape("https://example.com")
