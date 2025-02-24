import discord
import asyncio
import aiohttp
import re
import os
import logging
import random
from datetime import datetime
from config import (
    TOKEN,
    CHANNEL_ID,
    CHECK_URL,
    CHECK_INTERVAL,
    ERROR_INTERVAL,
    CACHE_FILE,
    HEALTH_CHECK_GREETING,
    CHATGPT_TOKEN,
    SYSTEM_PROMPT,
    GPT_MODEL
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Logs will go to stdout
)

# intents の設定（最低限必要なもの）
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 前回のサイト内容を保存する変数（初期値はファイルから読み込み）
previous_content = None
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            previous_content = f.read()
        logging.info("キャッシュファイルから前回の内容を読み込みました。")
    except Exception as e:
        logging.error(f"キャッシュファイルの読み込みに失敗しました: {e}")

def extract_titles(html: str):
    """
    指定された HTML から <h3 class="title01"><a href="...">Title</a></h3>
    の形式の (url, title) を抽出する関数。
    """
    pattern = r'<h3 class="title01">\s*<a href="([^"]+)">([^<]+)</a>\s*</h3>'
    return re.findall(pattern, html)

async def fetch_site_content(session, url: str):
    """サイトの内容を取得する関数"""
    async with session.get(url) as response:
        return await response.text()

def update_cache(new_content: str):
    """キャッシュファイルに新しいサイト内容を保存"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        logging.info("キャッシュファイルを更新しました。")
    except Exception as e:
        logging.error(f"キャッシュファイルの更新に失敗しました: {e}")

async def call_chatgpt_with_history(messages):
    """Calls the ChatGPT API using the entire conversation history."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {CHATGPT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GPT_MODEL,
        "messages": messages
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                answer = result["choices"][0]["message"]["content"].strip()
                return answer
            else:
                error = await response.text()
                logging.error(f"ChatGPT API request failed: {response.status} - {error}")
                return "申し訳ありませんが、エラーが発生しましたにゃ。"

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')
    # サイトチェック用のタスクを開始
    client.loop.create_task(check_website())

# Global conversation history (starts with system prompt)
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

@client.event
async def on_message(message):
    # Avoid responding to the bot's own messages
    if message.author == client.user:
        return

    # --- ChatGPT連携: ボットがメンションされた場合 ---
    if client.user in message.mentions:
        # Remove bot mentions from the message content
        prompt = (
            message.content.replace(f"<@{client.user.id}>", "")
                           .replace(f"<@!{client.user.id}>", "")
                           .strip()
        )
        if not prompt:
            await message.reply("何か質問してにゃ。")
            return

        # If the message is a reply (message.reference exists), continue the conversation.
        # Otherwise, reset the conversation history.
        if message.reference:
            # Append the new message to the existing conversation history.
            conversation_history.append({"role": "user", "content": prompt})
        else:
            # Clear the conversation history and start a new conversation.
            conversation_history.clear()
            conversation_history.append({"role": "system", "content": SYSTEM_PROMPT})
            conversation_history.append({"role": "user", "content": prompt})

        # Show a typing indicator while waiting for the reply.
        async with message.channel.typing():
            reply_text = await call_chatgpt_with_history(conversation_history)

        # Append the assistant's response to the conversation history.
        conversation_history.append({"role": "assistant", "content": reply_text})

        # Reply to the original message.
        await message.reply(reply_text)
        return

    # --- 既存のヘルスチェック: "hi, koneko" が含まれていれば ---
    if HEALTH_CHECK_GREETING in message.content.lower():
        cat_sounds = [
            "にゃーん", 
            "みゃーん", 
            "にゃおん", 
            "にゃっ", 
            "みゃっ", 
            "にゃ", 
            "みゃ", 
            "にゃ～", 
            "にゃん", 
            "にゃお",
            "うにゃにゃにゃにゃにゃ！"
        ]
        await message.channel.send(random.choice(cat_sounds))

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
                    logging.info("初回チェック完了。キャッシュファイルに保存しました。")
                else:
                    # 既存のタイトル一覧と新しいタイトル一覧を順序を保ったまま比較し、
                    # 前回のリストに存在しないものを「新規」として扱う。
                    old_list = extract_titles(previous_content)
                    new_list = extract_titles(content)

                    added_entries = [item for item in new_list if item not in old_list]
                    if added_entries:
                        channel = client.get_channel(CHANNEL_ID)
                        if channel:
                            # まとめて１つのメッセージにする
                            formatted_list = []
                            for (url, title) in added_entries:
                                formatted_list.append(f"タイトル: {title}\nURL: {url}")

                            titles_text = "\n\n".join(formatted_list)
                            await channel.send(
                                f"サイトが更新されましたにゃ！\n新しい記事:\n{titles_text}"
                            )
                            logging.info("更新を検知し、以下の内容で通知を送信しました:")
                            logging.info(titles_text)
                        else:
                            logging.error("指定したチャンネルが見つかりません。")
                        # 更新後の内容を保存（キャッシュファイルを更新）
                        previous_content = content
                        update_cache(content)
                    else:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        logging.info(f"更新は検知されませんでした。 現在の時刻: {current_time}")
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                logging.error(f"エラーが発生しました: {e}")
                await asyncio.sleep(ERROR_INTERVAL)

client.run(TOKEN)