import bcrypt

# プレーンテキストのパスワード
password = "popusmyz913"

# ハッシュ化
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# 表示
print(hashed.decode())
