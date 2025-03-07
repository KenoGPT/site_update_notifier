import os
from pygithub import Github
import openai
import config

PAT = getattr(config, 'PAT', '')
CHATGPT_TOKEN = config.CHATGPT_TOKEN
REPO_NAME = getattr(config, 'REPO_NAME', '')
BOT_FILE_PATH = getattr(config, 'BOT_FILE_PATH', '')
GPT_MODEL = config.GPT_MODEL

openai.api_key = CHATGPT_TOKEN

async def handle_dev_message(message: str) -> str:
    if not (PAT and CHATGPT_TOKEN and BOT_FILE_PATH and REPO_NAME):
        return "環境変数が設定されていません。"

    # GitHubからbot.pyの内容を取得
    try:
        g = Github(PAT)
        repo = g.get_repo(REPO_NAME)
        bot_file = repo.get_contents(BOT_FILE_PATH)
        bot_code = bot_file.decoded_content.decode("utf-8")
    except Exception as e:
        return f"GitHubからファイルの取得に失敗しました: {str(e)}"

    # GPTにコードとメッセージを送り、修正案をリクエスト
    prompt = f"""以下は現在のbot.pyの内容です：

    {bot_code}
    次の指示に従って、bot.pyのコードを修正してください。

    指示：
    {message}

    修正後のコードをマークダウン形式のコードブロックで示してください。
    """
    try:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        suggested_code = response['choices'][0]['message']['content']
    except Exception as e:
        return f"GPTによる修正案の取得に失敗しました: {str(e)}"

    return suggested_code