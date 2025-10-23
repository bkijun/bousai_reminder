from flask import Flask, request, abort
import json
import requests
import os

app = Flask(__name__)

# ======== 環境変数設定 =========
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_API_URL = "https://api.line.me/v2/bot/message"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# ======== JSONファイルでユーザー管理 =========
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# ======== LINEにメッセージを送信 =========
def send_message(user_id, text):
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    data = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(f"{LINE_API_URL}/push", headers=headers, json=data)

# ======== 天気情報取得 =========
def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&lang=ja&units=metric"
    res = requests.get(url)
    return res.json()

# ======== Webhook受信部分 =========
@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json()
    print("Webhook受信:", json.dumps(body, ensure_ascii=False))

    # イベントを解析
    try:
        event = body["events"][0]
        event_type = event["type"]
        user_id = event["source"]["userId"]

        users = load_users()

        # --- フォロー時（友だち追加） ---
        if event_type == "follow":
            users[user_id] = {"lat": None, "lon": None}
            save_users(users)
            send_message(user_id, "友だち追加ありがとうございます！📱\nあなたの地域の防災情報をお届けします。\nまず、位置情報を送信してください。")

        # --- 位置情報受信 ---
        elif event_type == "message" and event["message"]["type"] == "location":
            lat = event["message"]["latitude"]
            lon = event["message"]["longitude"]
            users[user_id] = {"lat": lat, "lon": lon}
            save_users(users)

            # 天気取得
            weather = get_weather(lat, lon)
            main = weather["weather"][0]["main"]
            temp = weather["main"]["temp"]

            # 条件分岐でメッセージ作成
            msg = f"現在の気温：{temp}℃\n天気：{main}\n"

            if main in ["Rain", "Thunderstorm"]:
                msg += "☔ 雨が降っています。防災チェックをしておきましょう。"
            elif temp >= 33:
                msg += "🥵 猛暑日です。熱中症に注意！"
            else:
                msg += "🌤 今のところ問題ありません。"

            send_message(user_id, msg)

    except Exception as e:
        print("エラー:", e)
        abort(400)

    return "OK"

# ======== テスト用ルート =========
@app.route("/")
def index():
    return "防災Bot稼働中"

# ======== メイン起動 =========
if __name__ == "__main__":
    app.run(port=5000)
