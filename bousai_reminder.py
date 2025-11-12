import os
import json
import requests
import datetime
import xml.etree.ElementTree as ET
import schedule
import time
from dotenv import load_dotenv

# ======== .env 読み込み ========
load_dotenv()

# ======== 環境変数設定 ========
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# ======== 神戸市の天気情報取得 ========
def get_weather():
    lat, lon = 34.6913, 135.1830  # 神戸市の座標
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall?"
        f"lat={lat}&lon={lon}&exclude=hourly,minutely,alerts&units=metric&appid={OPENWEATHER_API_KEY}&lang=ja"
    )
    res = requests.get(url)
    data = res.json()

    # データが取得できない場合の対策
    if "daily" not in data:
        print("⚠️ OpenWeatherのデータが取得できません:", data)
        return "不明", 0, 0, 0

    today = data["daily"][0]
    weather_main = today["weather"][0]["description"]
    temp_max = today["temp"]["max"]
    temp_min = today["temp"]["min"]
    current_temp = data["current"]["temp"]

    return weather_main, temp_max, temp_min, current_temp

# ======== 天気アイコン取得 =========
def get_weather_icon(description: str) -> str:
    if any(word in description for word in ["晴", "Clear"]):
        return "☀️"
    elif any(word in description for word in ["曇", "Cloud", "cloud"]):
        return "☁️"
    elif any(word in description for word in ["雨", "Rain", "Drizzle"]):
        return "🌧️"
    elif any(word in description for word in ["雷", "Thunder"]):
        return "⚡"
    elif any(word in description for word in ["雪", "Snow"]):
        return "❄️"
    return "🌈"

# ======== 気象庁XMLから兵庫県の警報を取得 ========
def get_jma_alerts():
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/other.xml"
    feed = requests.get(feed_url)
    feed.encoding = "utf-8"

    root = ET.fromstring(feed.text)
    namespace = {"atom": "http://www.w3.org/2005/Atom"}

    hyogo_url = None
    for entry in root.findall("atom:entry", namespace):
        title = entry.find("atom:title", namespace).text
        if "兵庫県の気象警報・注意報" in title:
            hyogo_url = entry.find("atom:id", namespace).text
            break

    if not hyogo_url:
        return "⚠️ 気象庁データが取得できませんでした。"

    xml_data = requests.get(hyogo_url)
    xml_data.encoding = "utf-8"
    alert_root = ET.fromstring(xml_data.text)

    alerts = []
    for area in alert_root.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}WarningArea"):
        area_name = area.find(
            "{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Area/{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Name"
        ).text
        events = [
            elem.text
            for elem in area.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Kind/{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Name")
        ]
        if events:
            alerts.append(f"【{area_name}】" + "・".join(events))

    if not alerts:
        return "✅ 現在、兵庫県に警報・注意報はありません。"

    return "⚠️ 兵庫県の警報・注意報\n" + "\n".join(alerts)

# ======== Discord送信 =========
def send_discord_message(content):
    data = {"content": content}
    res = requests.post(DISCORD_WEBHOOK_URL, json=data)
    print("Discord送信結果:", res.status_code, res.text)

# ======== メイン処理 =========
def main():
    today = datetime.date.today()
    weather_main, temp_max, temp_min, current_temp = get_weather()
    icon = get_weather_icon(weather_main)
    alerts = get_jma_alerts()

    msg = (
        f"📍 神戸市の天気（{today.strftime('%m/%d')}）\n"
        f"{icon} 今日の天気：{weather_main}\n"
        f"🌡️ 現在気温：{current_temp:.1f}℃\n"
        f"☀️ 最高気温：{temp_max:.1f}℃ / ❄️ 最低気温：{temp_min:.1f}℃\n"
        f"\n{alerts}\n"
    )

    # 月末メッセージ
    tomorrow = today + datetime.timedelta(days=1)
    if tomorrow.month != today.month:
        msg += "\n📅 月末です。防災用品・避難経路のチェックを行いましょう！"

    send_discord_message(msg)

# ======== スケジュール設定 =========
schedule.every().day.at("07:00").do(main)
print("✅ スケジュール設定完了：毎朝7時に通知します")

# 無限ループで常時実行
while True:
    schedule.run_pending()
    time.sleep(60)
