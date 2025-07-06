import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.p-world.co.jp/miyazaki/"

response = requests.get(url)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.text, 'html.parser')

shops = []

# 実際のHTML構造に合わせたテーブル取得
table = soup.find('table', attrs={'width':'600','cellpadding':'3'})

if table:
    rows = table.find_all('tr')[1:]  # ヘッダー行を除外

    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 4:
            shop_name = cols[1].get_text(strip=True)
            shop_address = cols[2].get_text(strip=True)

            machine_info = cols[3].get_text(strip=True).split('/')
            pachinko_count = machine_info[0].replace('台', '').strip() if len(machine_info) > 0 else '0'
            slot_count = machine_info[1].replace('台', '').strip() if len(machine_info) > 1 else '0'

            shops.append({
                '店舗名': shop_name,
                '住所': shop_address,
                'パチンコ台数': pachinko_count,
                'スロット台数': slot_count
            })
else:
    print("テーブルが見つかりませんでした。HTML構造を再確認してください。")

# Excelに書き出し
df = pd.DataFrame(shops)
df.to_excel("pachinko_shops.xlsx", index=False)
