# pachinko_detail_scraper.py

import re, time, pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def main():
    # ─── Chrome ドライバ準備 ─────────────────────────────────────────
    options = Options()
    options.add_argument('--headless')              # ヘッドレス実行
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )

    base_url  = "https://www.p-world.co.jp"
    list_url  = f"{base_url}/miyazaki/"

    # ─── 一覧ページ取得 ─────────────────────────────────────────────
    driver.get(list_url)
    time.sleep(2)

    # ─── 詳細ページURLを列挙 ───────────────────────────────────────
    links = driver.find_elements(By.TAG_NAME, "a")
    detail_urls = []
    pat = re.compile(r"^https://www\.p-world\.co\.jp/miyazaki/.+\.htm$")
    for a in links:
        href = a.get_attribute("href")
        if href and pat.match(href):
            detail_urls.append(href)
    detail_urls = list(dict.fromkeys(detail_urls))  # 重複除去

    print(f"詳細ページ数：{len(detail_urls)} 件")

    shops = []
    # ─── 各店舗詳細を巡回 ─────────────────────────────────────────
    for url in detail_urls:
        driver.get(url)
        time.sleep(1)

        # 【1】店舗名取得
        try:
            shop_name = driver.find_element(By.CSS_SELECTOR, "font[size='5']").text.strip()
        except:
            shop_name = ""

        # 【2】「住所」「台数」を含むテーブルを探す
        detail_table = None
        for tbl in driver.find_elements(By.TAG_NAME, "table"):
            txt = tbl.text
            if "住所" in txt and "台数" in txt:
                detail_table = tbl
                break

        # 存在しなければ空リスト
        if detail_table:
            cells = detail_table.find_elements(By.TAG_NAME, "td")
        else:
            cells = []

        address       = ""
        pachinko_cnt  = "0"
        slot_cnt      = "0"

        # 【3】tdを走査して「住所」「台数」を取得
        for i, td in enumerate(cells):
            text = td.text.strip()
            if text == "住所" and i+1 < len(cells):
                address = cells[i+1].text.strip()
            if text == "台数" and i+1 < len(cells):
                machines = cells[i+1].text.strip().split("/")
                if machines:
                    pachinko_cnt = machines[0].replace("台","").strip()
                if len(machines) > 1:
                    slot_cnt = machines[1].replace("台","").strip()

        shops.append({
            "店舗名":       shop_name,
            "住所":         address,
            "パチンコ台数": pachinko_cnt,
            "スロット台数": slot_cnt,
            "詳細URL":      url
        })
        print(f"取得完了 → {shop_name}")

    driver.quit()

    # ─── Excelへ書き出し ───────────────────────────────────────────
    df = pd.DataFrame(shops)
    df.to_excel("pachinko_shops.xlsx", index=False)
    print("完了：pachinko_shops.xlsx を出力しました。")

if __name__ == "__main__":
    main()
