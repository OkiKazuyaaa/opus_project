from collections import defaultdict
from flask import Flask, request, send_file, render_template
import pandas as pd
import requests
from bs4 import BeautifulSoup
import csv
import sys
import tempfile
import os
import calendar
from datetime import datetime, timedelta
import time
import re

app = Flask(__name__)

def resource_path(relative_path):
    try:
        # PyInstaller でパッケージされた場合
        base_path = sys._MEIPASS
    except Exception:
        # 通常のスクリプト実行時
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

station_df = pd.read_csv(resource_path('data/area_data.csv'))

prefecture_map = {
    "宗谷地方":"11","上川地方":"12","留萌地方":"13","石狩地方":"14","空知地方":"15","後志地方":"16",
    "網走地方":"17","根室地方":"18","釧路地方":"19","十勝地方":"20","胆振地方":"21","日高地方":"22",
    "渡島地方":"23","檜山地方":"24","青森県":"31","秋田県":"32","岩手県":"33","宮城県":"34",
    "山形県":"35","福島県":"36","茨城県":"40","栃木県":"41","群馬県":"42","埼玉県":"43",
    "東京都":"44","千葉県":"45","神奈川県":"46","長野県":"48","山梨県":"49","静岡県":"50",
    "愛知県":"51","岐阜県":"52","三重県":"53","新潟県":"54","富山県":"55","石川県":"56",
    "福井県":"57","滋賀県":"60","京都府":"61","大阪府":"62","兵庫県":"63","奈良県":"64",
    "和歌山県":"65","岡山県":"66","広島県":"67","島根県":"68","鳥取県":"69","徳島県":"71",
    "香川県":"72","愛媛県":"73","高知県":"74","山口県":"81","福岡県":"82","大分県":"83",
    "長崎県":"84","佐賀県":"85","熊本県":"86","宮崎県":"87","鹿児島県":"88","沖縄県":"91",
    "南極":"99"
}

@app.route('/')
def index():
    station_dict = {}
    for _, row in station_df.iterrows():
        prec_code = str(row['prec_no']).zfill(2)
        station_name = row['station_name']
        for pref_name, code in prefecture_map.items():
            if code == prec_code:
                station_dict.setdefault(pref_name, set()).add(station_name)
    station_dict = {k: sorted(v) for k, v in station_dict.items()}
    return render_template('index3.html', station_dict=station_dict)

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

from collections import Counter

@app.route('/download', methods=['POST'])
def download():
    year = int(request.form['year'])
    month = int(request.form['month'])
    prefecture = request.form['prefecture']
    station = request.form['station']

    pref_code = prefecture_map.get(prefecture)
    if not pref_code:
        return "都道府県名が不正です。"

    station_input=station.strip()
    print(f"[DEBUG] ユーザー入力 station: {station}, prefecture: {prefecture}, prefecture_code: {pref_code}")
    print("[DEBUG] 該当都道府県内の候補 station 名:")
    print(station_df[station_df['prec_no'].astype(str).str.zfill(2) == pref_code]['station_name'].tolist())

    match = station_df[
        (station_df['prec_no'].astype(str).str.zfill(2) == pref_code) &
        (station_df['station_name'].str.contains(station_input,na=False))
    ]
    if match.empty:
        return "地点が見つかりませんでした"

    prec_no = match.iloc[0]['prec_no']
    block_no = match.iloc[0]['block_no']
    block_no_str=str(block_no).zfill(4)

    
    filepath=f'data/{year}_{month}_{station}_hourly.csv'
    dirpath=os.path.dirname(filepath)
    os.makedirs(dirpath,exist_ok=True)

    all_rows_dicts=[]
    header_counter=Counter()

    start_date=datetime(year,month,1)
    end_date=start_date+timedelta(days=calendar.monthrange(year,month)[1]-1)
    current_date=start_date

    while current_date <= end_date:
        url_candidates = [
            f"https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php?prec_no={prec_no}&block_no={block_no}&year={current_date.year}&month={current_date.month}&day={current_date.day}&view=",
            f"https://www.data.jma.go.jp/stats/etrn/view/hourly_a1.php?prec_no={prec_no}&block_no={block_no_str}&year={current_date.year}&month={current_date.month:02d}&day={current_date.day:02d}&view=p1"
        ]
         
        table=None
        for url in url_candidates:
            res=requests.get(url)
            if res.status_code==200:
                 soup=BeautifulSoup(res.content,'html.parser')
                 table=soup.find("table",class_="data2_s")
                 if table:
                     print(f"[INFO]データ取得成功:{url}")
                     break
            else:
                print(f"[WARN]試行URLの取得に失敗:{url},status={res.status_code}")

        if not table:
            print(f"[エラー]{current_date}の取得に失敗(2候補ともNG)")
            current_date+=timedelta(days=1)
            continue
    
        current_headers=parse_table_headers(table)
        header_counter.update(current_headers)
    
        for tr in table.find_all("tr"):
            cells=tr.find_all(['td','th'])
            if not cells:
                continue
            first_col=cells[0].get_text(strip=True)
            if not first_col.isdigit():
                continue

            cols=[]
            for td in cells:
                img=td.find('img')
                if img and img.has_attr('alt'):
                    cols.append(img['alt'].strip())
                else:
                    text=td.get_text(strip=True).replace('×','').replace('--','')
                    text=text if text else None
                    cols.append(text)
    

            if len(cols) !=len(current_headers):
                print(f"[警告]列数不一致-スキップ:{current_date},時間={first_col},期待列数={len(current_headers)},実際列数={len(cols)}")
                continue
                
            row_dict={header: cols[i] if i < len(cols) else ''for i, header in enumerate(current_headers)}
            all_rows_dicts.append(row_dict)

        current_date += timedelta(days=1)
        time.sleep(1)

    if not all_rows_dicts:
        return "データが取得できませんでした。"
    
    
    final_headers=[h for h, _ in header_counter.most_common()]
    final_rows=[[row.get(h,'')for h in final_headers]for row in all_rows_dicts]
    
    safe_station = re.sub(r'[\\/*?:"<>|]',"",station)
    filename=f"{year}_{month}_{station}_hourly.csv"
    
    output_dir=tempfile.gettempdir()
    filepath=os.path.join(output_dir,filename)
    
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(final_headers)
        writer.writerows(final_rows)

    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
