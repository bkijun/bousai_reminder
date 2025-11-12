import json
import requests
import os
import datetime
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# ======== .env 読み込み ========
load_dotenv()

# ======== 環境変数設定 ========
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

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
    else:
        return "🌈"

# ======== 神戸市の天気情報取得 ========
def get_weather():
    lat, lon = 34.6913, 135.1830  # 神戸市の座標
    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_API_KEY}&lang=ja"
    )
    res = requests.get(url)
    data = res.json()

    weather_main = data["weather"][0]["description"]
    temp_now = data["main"]["temp"]
    temp_max = data["main"]["temp_max"]
    temp_min = data["main"]["temp_min"]

    return weather_main, temp_now, temp_max, temp_min

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
        area_name = area.find("{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Area/{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Name").text
        events = [elem.text for elem in area.findall(".//{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Kind/{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}Name")]
        if events:
            alerts.append(f"【{area_name}】" + "・".join(events))

    if not alerts:
        return "✅ 現在、兵庫県に警報・注意報はありません。"

    return "⚠️ 兵庫県の警報・注意報\n" + "\n".join(alerts)

# ======== Discord送信 =========
def send_discord_message(content):
    data = {"content": content}
    res = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if res.status_code == 204:
        print("✅ Discord通知を送信しました。")
    else:
        print("❌ Discord送信エラー:", res.text)

# ======== メイン処理 =========
def main():
    today = datetime.date.today()

    # 天気情報取得
    weather_main, temp_now, temp_max, temp_min = get_weather()
    icon = get_weather_icon(weather_main)

    # メッセージ作成
    msg = (
        f"📍神戸市の天気（{today.strftime('%m/%d')}）\n"
        f"{icon} 今日の天気：{weather_main}\n"
        f"🌡️ 現在の気温：{temp_now:.1f}℃\n"
        f"⬆️ 最高気温：{temp_max:.1f}℃\n"
        f"⬇️ 最低気温：{temp_min:.1f}℃\n"
    )

    # 警報
    alerts = get_jma_alerts()
    msg += "\n" + alerts + "\n"

    # 注意メッセージ
    if any(word in weather_main for word in ["雨", "雷", "Rain", "Thunderstorm"]):
        msg += "☔ 雨の可能性があります。防災チェックをしておきましょう。\n"
    elif temp_max >= 35:
        msg += "🥵 猛暑日です。熱中症に注意してください。\n"

    # 月末メッセージ
    tomorrow = today + datetime.timedelta(days=1)
    if tomorrow.month != today.month:
        msg += "\n📅 月末です。防災用品・避難経路のチェックを行いましょう！"

    # Discord送信
    send_discord_message(msg)


if __name__ == "__main__":
    main()
