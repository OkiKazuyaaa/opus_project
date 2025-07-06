import bcrypt
import json

# --- プレーンなUSER_DB（元データ） ---
USER_DB_PLAIN = {
    "miyazaki@example.com": {"password": "popusmyz913", "store_name": "オーパス宮崎本店"},
    "komatsu@example.com": {"password": "qopuskmt671", "store_name": "オーパス小松"},
    "takanabe@example.com": {"password": "dopustkn237", "store_name": "オーパス高鍋"},
    "nichinan@example.com": {"password": "lopusntn378", "store_name": "オーパス日南"},
    "nobeoka@example.com": {"password": "mopusnbo098", "store_name": "オーパス延岡"},
    "mimata@example.com": {"password": "vopusmmt881", "store_name": "オーパス三股"},
    "miyakonojo@example.com": {"password": "aopusmyk733", "store_name": "オーパス都城"},
    "kanoya@example.com": {"password": "gopuskny182", "store_name": "オーパス鹿屋"},
    "kokoronohitomi2003@keio.jp": {"password": "123pwpw", "store_name": "管理者"}
}

# --- ハッシュ形式に変換 ---
hashed_user_db = {}
for email, info in USER_DB_PLAIN.items():
    hashed = bcrypt.hashpw(info["password"].encode(), bcrypt.gensalt()).decode()
    hashed_user_db[email] = {
        "password_hash": hashed,
        "store_name": info["store_name"]
    }

# --- 保存先（例：users.json）---
with open("users.json", "w", encoding="utf-8") as f:
    json.dump(hashed_user_db, f, indent=2, ensure_ascii=False)

print("✅ users.json に保存しました！")
