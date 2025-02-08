import discord
import asyncio
import aiohttp
import re
import os
from datetime import datetime
from config import TOKEN, CHANNEL_ID, CHECK_URL, CHECK_INTERVAL, ERROR_INTERVAL, CACHE_FILE

# intents の設定（最低限必要なもの）
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# 前回のサイト内容を保存する変数（初期値はファイルから読み込み）
previous_content = None
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            previous_content = f.read()
        print("キャッシュファイルから前回の内容を読み込みました。")
    except Exception as e:
        print(f"キャッシュファイルの読み込みに失敗しました: {e}")

def extract_titles(html):
    """
    指定された HTML から <h3 class="title01"><a href="...">Title</a></h3>
    の形式の URL とタイトルを抽出する関数
    Returns a list of tuples (url, title).
    """
    pattern = r'<h3 class="title01">\s*<a href="([^"]+)">([^<]+)</a>\s*</h3>'
    entries = re.findall(pattern, html)
    return entries

async def fetch_site_content(session, url):
    """
    サイトの内容を取得する関数
    """
    async with session.get(url) as response:
        return await response.text()

def update_cache(new_content):
    """
    キャッシュファイルに新しいサイト内容を保存する
    """
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("キャッシュファイルを更新しました。")
    except Exception as e:
        print(f"キャッシュファイルの更新に失敗しました: {e}")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    # サイトチェック用のタスクを開始
    client.loop.create_task(check_website())

async def check_website():
    """
    定期的にサイトの内容をチェックし、更新があれば通知するタスク
    """
    global previous_content
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                content = await fetch_site_content(session, CHECK_URL)
                if previous_content is None:
                    # 初回実行時は前回の内容として保存
                    previous_content = content
                    update_cache(content)
                    print("初回チェック完了。キャッシュファイルに保存しました。")
                else:
                    # 抽出された (URL, タイトル) のリストを比較
                    old_entries = set(extract_titles(previous_content))
                    new_entries = set(extract_titles(content))
                    added_entries = new_entries - old_entries
                    if added_entries:
                        channel = client.get_channel(CHANNEL_ID)
                        if channel:
                            # 各エントリを「タイトル：... \nURL：...」形式でフォーマット
                            messages = [f"タイトル: {title}\nURL: {url}" for url, title in added_entries]
                            titles_text = "\n\n".join(messages)
                            await channel.send(f"サイトが更新されました！\n新しい記事:\n{titles_text}")
                            print("更新を検知し、以下の内容で通知を送信しました:")
                            print(titles_text)
                        else:
                            print("指定したチャンネルが見つかりません。")
                        # 更新後の内容を保存（キャッシュファイルを更新）
                        previous_content = content
                        update_cache(content)
                    else:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"更新は検知されませんでした。 現在の時刻: {current_time}")
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                print(f"エラーが発生しました: {e}")
                await asyncio.sleep(ERROR_INTERVAL)

client.run(TOKEN)
