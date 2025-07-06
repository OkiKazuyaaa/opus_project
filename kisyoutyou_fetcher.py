# kisyoutyou_fetcher.py
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import time
from collections import defaultdict, Counter

station_df = pd.read_csv('data/area_data.csv', encoding='utf-8')

prefecture_map = {
    "宮崎県": "87",  # 必要に応じて拡張
}

def parse_table_headers(table):
    header_rows = [tr for tr in table.find_all("tr") if tr.find("th")]
    grid = defaultdict(str)
    row_index = 0
    max_columns = 0

    for tr in header_rows:
        col_index = 0
        for cell in tr.find_all(['th', 'td']):
            while grid[(row_index, col_index)]:
                col_index += 1
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            text = cell.get_text(strip=True)
            for i in range(rowspan):
                for j in range(colspan):
                    if i == rowspan - 1:
                        grid[(row_index + i, col_index + j)] = text
            max_columns = max(max_columns, col_index + colspan)
            col_index += colspan
        row_index += 1

    headers = []
    for col in range(max_columns):
        parts = [grid[(row, col)] for row in range(row_index)]
        seen = set()
        cleaned = []
        for part in parts:
            if part and part not in seen:
                seen.add(part)
                cleaned.append(part)
        headers.append("_".join(cleaned))
    return headers

def fetch_weather_csv(year, month, prefecture, station_name, out_path):
    pref_code = prefecture_map.get(prefecture)
    match = station_df[
        (station_df['prec_no'].astype(str).str.zfill(2) == pref_code) &
        (station_df['station_name'].str.contains(station_name, na=False))
    ]
    if match.empty:
        raise ValueError("該当観測所が見つかりません")

    prec_no = match.iloc[0]['prec_no']
    block_no = str(match.iloc[0]['block_no']).zfill(4)

    all_rows_dicts = []
    header_counter = Counter()

    start_date = datetime(year, month, 1)
    end_date = start_date + timedelta(days=31)
    end_date = end_date.replace(day=1) - timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        url = f"https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php?prec_no={prec_no}&block_no={block_no}&year={current_date.year}&month={current_date.month}&day={current_date.day}&view="
        res = requests.get(url)
        if res.status_code != 200:
            current_date += timedelta(days=1)
            continue
        soup = BeautifulSoup(res.content, 'html.parser')
        table = soup.find("table", class_="data2_s")
        if not table:
            current_date += timedelta(days=1)
            continue
        current_headers = parse_table_headers(table)
        header_counter.update(current_headers)

        for tr in table.find_all("tr"):
            cells = tr.find_all(['td', 'th'])
            if not cells or not cells[0].get_text(strip=True).isdigit():
                continue
            row_data = []
            for td in cells:
                img = td.find('img')
                if img and img.has_attr('alt'):
                    row_data.append(img['alt'].strip())
                else:
                    txt = td.get_text(strip=True).replace("×", "").replace("--", "")
                    row_data.append(txt if txt else None)
            if len(row_data) != len(current_headers):
                continue
            row_dict = {current_headers[i]: row_data[i] for i in range(len(current_headers))}
            all_rows_dicts.append(row_dict)

        current_date += timedelta(days=1)
        time.sleep(1)

    df = pd.DataFrame(all_rows_dicts)
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    return out_path
