from supabase import create_client
from dotenv import load_dotenv
import os

# 環境変数ロード
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

# テストユーザー作成
users = [
    ("userA@companyA.com", "passwordA", "company-A-uuid"),
    ("userB@companyB.com", "passwordB", "company-B-uuid"),
]
for email, pw, cid in users:
    res = supabase.auth.sign_up(
        {"email": email, "password": pw},
        {"data": {"company_id": cid}}
    )
    print(res)