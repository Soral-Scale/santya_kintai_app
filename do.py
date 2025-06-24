import sqlite3

# sample.dbファイルに接続（存在しなければ新規作成される）
conn = sqlite3.connect('sample.db')

# カーソル生成
cur = conn.cursor()

# テーブル作成
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
''')

# コミット
conn.commit()

# 接続終了
conn.close()