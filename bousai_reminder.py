import json, requests, os, datetime
from dotenv import load_dotenv   

# ======== .env 読み込み ========
load_dotenv()   

# ======== 環境変数設定 ========
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
LINE_API_URL = "https://api.line.me/v2/bot/message/push"
USERS_FILE = "users.json"

# ======== ユーザー読み込み =========
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ======== 天気情報取得 (One Call API) ========
def get_weather(lat, lon):
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall?"
        f"lat={lat}&lon={lon}&exclude=hourly,minutely,alerts&units=metric&appid={OPENWEATHER_API_KEY}&lang=ja"
    )
    res = requests.get(url)
    data = res.json()

    # 今日のデータを取得
    today = data["daily"][0]
    weather_main = today["weather"][0]["description"]  # "晴れ" など
    temp_max = today["temp"]["max"]
    temp_min = today["temp"]["min"]

    return weather_main, temp_max, temp_min


# ======== LINE送信 =========
def send_message(user_id, text):
    headers = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}"}
    data = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    requests.post(LINE_API_URL, headers=headers, json=data)

# ======== メイン処理 =========
def main():
    users = load_users()
    today = datetime.date.today()

    for user_id, info in users.items():
        lat = info.get("lat")
        lon = info.get("lon")
        if not lat or not lon:
            continue

        weather_main, temp_max, temp_min = get_weather(lat, lon)
        msg = f"今日の天気：{weather_main}\n最高気温：{temp_max:.1f}℃\n最低気温：{temp_min:.1f}℃\n"

        if weather_main in ["Rain", "Thunderstorm"]:
            msg += "☔ 雨の可能性があります。防災チェックをしておきましょう。\n"
        elif temp_max >= 35:
            msg += "🥵 猛暑日です。熱中症に注意してください。\n"

        # --- 月末なら追加メッセージ ---
        tomorrow = today + datetime.timedelta(days=1)
        if tomorrow.month != today.month:
            msg += "\n📅 月末です。防災用品・避難経路のチェックを行いましょう！"

        send_message(user_id, msg)
        print(f"{user_id} に送信しました。")

if __name__ == "__main__":
    main()
