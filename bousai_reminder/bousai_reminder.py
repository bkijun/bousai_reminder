import os
import requests
import datetime
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import discord
from discord.ext import commands

# ======== 環境変数読み込み ========
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# ======== 天気取得（神戸市）========
def get_weather():
    try:
        lat, lon = 34.6913, 135.1830
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_API_KEY}&lang=ja"
        )
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        weather = data["weather"][0]["description"]
        temp_current = data["main"]["temp"]
        temp_max = data["main"]["temp_max"]
        temp_min = data["main"]["temp_min"]
        return weather, temp_current, temp_max, temp_min

    except Exception as e:
        print(f"[Error] 天気取得失敗: {e}")
        return "不明", 0, 0, 0

# ======== 警報・注意報取得（気象庁XML） ========
def get_jma_alerts():
    try:
        # 気象庁フィード
        feed_url = "https://www.data.jma.go.jp/developer/xml/feed/other.xml"
        feed = requests.get(feed_url, timeout=10)
        feed.raise_for_status()

        root = ET.fromstring(feed.text)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}

        hyogo_url = None

        # 兵庫県の警報URLを探す
        for entry in root.findall("atom:entry", namespace):
            title = entry.find("atom:title", namespace).text
            if "兵庫県の気象警報・注意報" in title:
                hyogo_url = entry.find("atom:id", namespace).text
                break

        if not hyogo_url:
            return "✅ 現在、兵庫県に警報・注意報はありません。"

        # 警報XML本体を取得
        xml_data = requests.get(hyogo_url, timeout=10)
        xml_data.raise_for_status()

        alert_root = ET.fromstring(xml_data.text)

        # ========== 発表時刻(Report DateTime) ==========
        report = alert_root.find(".//{http://xml.kishou.go.jp/jmaxml1/information}Report")
        report_time = "不明"

        if report is not None:
            report_time = report.attrib.get("DateTime", "不明")
            # 例: 2025-01-01T12:00:00+09:00 → 2025/01/01 12:00
            report_time = report_time.replace("T", " ").split("+")[0].replace("-", "/")[:-3]

        # ========== 警報内容取得 ==========
        alerts = []
        warn_ns = "{http://xml.kishou.go.jp/jmaxml1/body/meteorology1/}"

        for area in alert_root.findall(f".//{warn_ns}WarningArea"):
            area_name = area.find(f".//{warn_ns}Name").text

            kinds = [
                elem.text
                for elem in area.findall(
                    f".//{warn_ns}Kind/{warn_ns}Name"
                )
            ]

            if kinds:
                alerts.append(f"【{area_name}】" + "・".join(kinds))

        if not alerts:
            return "✅ 現在、兵庫県に警報・注意報はありません。"

        # 最終メッセージ組み立て
        alert_msg = (
            "⚠️ **兵庫県 気象警報・注意報**\n"
            + "\n".join(alerts)
            + f"\n警報・注意報 発表：{report_time}"
        )

        return alert_msg

    except Exception as e:
        print(f"[Error] 警報情報取得失敗: {e}")
        return "⚠️ 警報情報を取得できませんでした。"


# ======== 月末の防災チェック ========
def get_monthly_bousai_check():
    today = datetime.date.today()
    last_day = (today.replace(day=28) + datetime.timedelta(days=4))
    last_day = last_day.replace(day=1) - datetime.timedelta(days=1)

    if today.day == last_day.day:
        check_items = [
            "🧯 **防災チェック（月末）**",
            "・非常食・水の賞味期限チェック",
            "・モバイルバッテリー充電",
            "・懐中電灯の電池確認",
            "・救急セットの補充",
            "・避難経路の確認",
            "・非常持ち出し袋の見直し",
        ]
        return "\n".join(check_items)

    return ""  # 月末以外は何も返さない


# ======== Discord通知 ========
async def send_discord_message():
    weather, temp_current, temp_max, temp_min = get_weather()
    alerts = get_jma_alerts()
    bousai = get_monthly_bousai_check()

    today = datetime.date.today().strftime("%m/%d")

    msg = (
        f"📍 **神戸市の天気（{today}）**\n"
        f"☀️ 天気：{weather}\n"
        f"🌡 現在：{temp_current:.1f}℃\n"
        f"⬆ 最高：{temp_max:.1f}℃\n"
        f"⬇ 最低：{temp_min:.1f}℃\n\n"
        f"{alerts}\n"
    )

    if bousai != "":
        msg += f"\n{bousai}\n"

    msg += "\n@everyone"

    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(msg)


# ======== Bot設定 ========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} がログインしました")

    # 起動したら即送信（テスト用）
    await send_discord_message()

    await bot.close()


bot.run(TOKEN)
