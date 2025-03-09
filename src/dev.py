from github import Github
from openai import OpenAI
import uuid
from config import config
from .file_utils import get_file_from_repo

PAT = getattr(config, "PAT", "")
CHATGPT_TOKEN = config.CHATGPT_TOKEN
REPO_NAME = getattr(config, "REPO_NAME", "")
BOT_FILE_PATH = getattr(config, "BOT_FILE_PATH", "")
FORKED_REPO_NAME = getattr(config, "FORKED_REPO_NAME", "")
GPT_MODEL = config.GPT_MODEL


def generate_branch_name(prefix="auto-fix-"):
    unique_id = uuid.uuid4().hex[:8]  # UUIDから8文字取得
    return f"{prefix}{unique_id}"


client = OpenAI(api_key=CHATGPT_TOKEN)


async def handle_dev_message(message: str) -> str:
    if not (PAT and CHATGPT_TOKEN and BOT_FILE_PATH and REPO_NAME and FORKED_REPO_NAME):
        return "環境変数が設定されていません。"

    bot_file = get_file_from_repo(config.BOT_FILE_PATH)

    if bot_file is None:
        return "GitHubからファイルの取得に失敗しました。"

    try:
        g = Github(PAT)
        repo = g.get_repo(FORKED_REPO_NAME)

        bot_code = bot_file.decoded_content.decode("utf-8")
        branch_name = generate_branch_name()
        sb = repo.get_branch("main")
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sb.commit.sha)
        commit_message = "GPTによる自動修正を適用"

    except Exception as e:
        return f"GitHubからファイルの取得に失敗しました: {str(e)}"

    # GPTにコードとメッセージを送り、修正案をリクエスト
    prompt = f"""以下は現在のbot.pyの内容です：

    {bot_code}
    次の指示に従って、bot.pyのコードを修正してください。

    指示：
    {message}

    必ず修正後のコードのみを返信してください（説明文なしで）。
    """
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL, messages=[{"role": "user", "content": prompt}]
        )
        suggested_code = response.choices[0].message.content
        if not suggested_code:
            return "コードの生成に失敗しました。"

        repo.update_file(
            bot_file.path,
            commit_message,
            suggested_code,
            bot_file.sha,
            branch=branch_name,
        )

    except Exception as e:
        return f"GPTによる修正案の取得に失敗しました: {str(e)}"

    return f"GPTによる修正案をブランチ「{branch_name}」にpushしました。"
