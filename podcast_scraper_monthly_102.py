import socket
_orig_getaddrinfo = socket.getaddrinfo
def _force_ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _force_ipv4_getaddrinfo

import os
import requests
import xml.etree.ElementTree as ET
import psycopg2
from datetime import datetime, timezone, timedelta

# 從環境變數取得 Supabase 資料庫連線字串
SUPABASE_DB_URL = os.environ.get('SUPABASE_DB_URL')
if not SUPABASE_DB_URL:
    raise Exception("請設定環境變數 SUPABASE_DB_URL，並將 Supabase 的連線字串貼上。")

# 連線到 Supabase PostgreSQL，啟用 SSL
conn = psycopg2.connect(SUPABASE_DB_URL, sslmode='require')
cursor = conn.cursor()

# 設定台北時區 (UTC+8)
taipei_tz = timezone(timedelta(hours=8))

# 根據當前日期產生動態資料表名稱（例如：podcasts_202601）
current_month = datetime.now(taipei_tz).strftime("%Y%m")
table_name = f"podcasts_{current_month}"
print(f"本次執行將資料儲存至資料表：{table_name}")

# 建立當月資料表（若尚未存在）
cursor.execute(f'''
CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    date TEXT,
    category TEXT,
    rank TEXT,
    title TEXT,
    host TEXT
)
''')
conn.commit()

# 開啟 RLS（消除 Supabase Dashboard 警告，postgres 角色會繞過此限制）
cursor.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")
conn.commit()
print(f"資料表 {table_name} 已開啟 Row Level Security")

# 更新序列的值，以避免重複主鍵問題
cursor.execute(f"SELECT setval('{table_name}_id_seq', COALESCE((SELECT MAX(id) FROM {table_name}) + 1, 1), false);")
conn.commit()

# 定義各類別對應的 genre 參數（完整版：包含所有主類別與子類別）
genre_mapping = {
    "熱門": None,
    
    # 藝術
    "藝術": "1301",
    "書籍": "1482",
    "設計": "1402",
    "時尚與美容": "1459",
    "食物": "1306",
    "表演": "1405",
    "視覺藝術": "1406",
    
    # 商業
    "商業": "1321",
    "職業": "1410",
    "創業": "1493",
    "投資": "1412",
    "管理": "1491",
    "行銷": "1492",
    "非營利": "1494",
    
    # 喜劇
    "喜劇": "1303",
    "喜劇訪談": "1496",
    "即興表演": "1495",
    "脫口秀": "1497",
    
    # 教育
    "教育": "1304",
    "課程": "1501",
    "教學": "1499",
    "語言學習": "1498",
    "自我成長": "1500",
    
    # 小說
    "小說": "1483",
    "喜劇小說": "1486",
    "戲劇": "1484",
    "科幻小說": "1485",
    
    # 政府
    "政府": "1511",
    
    # 歷史
    "歷史": "1487",
    
    # 健康與瘦身
    "健康與瘦身": "1512",
    "另類醫學": "1513",
    "瘦身": "1514",
    "醫學": "1518",
    "心理健康": "1517",
    "營養健康": "1515",
    "兩性": "1516",
    
    # 兒童與家庭
    "兒童與家庭": "1305",
    "兒童教育": "1519",
    "子女教養": "1521",
    "寵物與動物": "1522",
    "兒童故事": "1520",
    
    # 休閒
    "休閒": "1502",
    "動漫畫": "1510",
    "汽車": "1503",
    "航空": "1504",
    "手工": "1506",
    "遊戲": "1507",
    "嗜好": "1505",
    "居家與園藝": "1508",
    "電子遊戲": "1509",
    
    # 音樂
    "音樂": "1310",
    "音樂評論": "1523",
    "音樂史": "1524",
    "音樂訪談": "1525",
    
    # 新聞
    "新聞": "1489",
    "商業新聞": "1490",
    "每日新聞": "1526",
    "娛樂新聞": "1531",
    "新聞評論": "1530",
    "政治": "1527",
    "體育新聞": "1529",
    "科技新聞": "1528",
    
    # 宗教與精神生活
    "宗教與精神生活": "1314",
    "佛教": "1438",
    "基督教": "1439",
    "印度教": "1463",
    "伊斯蘭教": "1440",
    "猶太教": "1441",
    "宗教": "1532",
    "靈修": "1444",
    
    # 科學
    "科學": "1533",
    "天文學": "1538",
    "化學": "1539",
    "地球科學": "1540",
    "生命科學": "1541",
    "數學": "1536",
    "自然科學": "1534",
    "大自然": "1537",
    "物理學": "1542",
    "社會科學": "1535",
    
    # 社會與文化
    "社會與文化": "1324",
    "紀實": "1543",
    "個人日誌": "1302",
    "哲學": "1443",
    "名勝與旅遊": "1320",
    "人際關係": "1544",
    
    # 運動
    "運動": "1545",
    "棒球": "1549",
    "籃球": "1548",
    "板球": "1554",
    "夢幻體育": "1560",
    "美式足球": "1547",
    "高爾夫": "1553",
    "曲棍球": "1550",
    "橄欖球": "1552",
    "跑步": "1551",
    "足球": "1546",
    "游泳": "1558",
    "網球": "1556",
    "排球": "1557",
    "野外": "1559",
    "摔角": "1555",
    
    # 科技
    "科技": "1318",
    
    # 犯罪紀實
    "犯罪紀實": "1488",
    
    # 電視與電影
    "電視與電影": "1309",
    "節目回顧": "1562",
    "電影史": "1564",
    "電影訪談": "1565",
    "電影評論": "1563",
    "電視節目評論": "1561"
}

# Apple RSS feed 的 URL（台灣地區，限制 200 筆資料）
base_url = "https://itunes.apple.com/tw/rss/toppodcasts/limit=200/{}xml"

# 定義 XML 解析時使用的命名空間
ns = {
    'atom': 'http://www.w3.org/2005/Atom',
    'im': 'http://itunes.apple.com/rss'
}

for category, genre in genre_mapping.items():
    if genre:
        rss_url = base_url.format(f"genre={genre}/")
    else:
        rss_url = base_url.format("")
    
    print(f"開始處理類別：{category}，RSS URL：{rss_url}")
    try:
        response = requests.get(rss_url)
        response.raise_for_status()
    except Exception as e:
        print(f"取得 URL {rss_url} 時發生錯誤：{e}")
        continue

    try:
        root = ET.fromstring(response.content)
    except Exception as e:
        print(f"解析 RSS XML 時發生錯誤（{rss_url}）：{e}")
        continue

    # 取得所有 <entry> 節點，每個 entry 代表一筆排行榜資料
    entries = root.findall('atom:entry', ns)
    print(f"類別 {category} 共找到 {len(entries)} 筆資料")

    # 取得目前日期與時間（台北時間）
    current_datetime = datetime.now(taipei_tz).strftime("%Y/%m/%d %H:%M")

    # 遍歷所有資料，依序編號作為排行榜名次
    for index, entry in enumerate(entries, start=1):
        title_elem = entry.find('im:name', ns)
        title = title_elem.text.strip() if title_elem is not None else "未知標題"
        artist_elem = entry.find('im:artist', ns)
        host = artist_elem.text.strip() if artist_elem is not None else "未知主持人"
        rank = str(index)

        cursor.execute(f'''
            INSERT INTO {table_name} (date, category, rank, title, host)
            VALUES (%s, %s, %s, %s, %s)
        ''', (current_datetime, category, rank, title, host))
    
    conn.commit()
    print(f"類別 {category} 的資料已儲存至 Supabase 資料庫。")

cursor.close()
conn.close()
print("所有資料已處理完成，資料庫連線已關閉。")