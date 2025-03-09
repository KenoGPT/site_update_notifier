import json
import uuid
from github import Github
from openai import OpenAI
from config import config
from .github_utils import get_file_from_repo, get_all_file_paths

PAT = getattr(config, "PAT", "")
CHATGPT_TOKEN = config.CHATGPT_TOKEN
REPO_NAME = getattr(config, "REPO_NAME", "")
FORKED_REPO_NAME = getattr(config, "FORKED_REPO_NAME", "")
GPT_MODEL = config.GPT_MODEL


def generate_branch_name(prefix="auto-fix-"):
    unique_id = uuid.uuid4().hex[:8]  # UUIDから8文字取得
    return f"{prefix}{unique_id}"


client = OpenAI(api_key=CHATGPT_TOKEN)


async def handle_dev_message(message: str) -> str:
    if not (PAT and CHATGPT_TOKEN and REPO_NAME and FORKED_REPO_NAME):
        return "環境変数が設定されていません。"
    file_paths = get_all_file_paths("src")
    files_content = {}
    for file_path in file_paths:
        file = get_file_from_repo(file_path)
        if file is None:
            return f"GitHubからファイル「{file_path}」の取得に失敗しました。"
        files_content[file_path] = file.decoded_content.decode("utf-8")

    g = Github(PAT)
    repo = g.get_repo(FORKED_REPO_NAME)
    branch_name = generate_branch_name()

    try:
        sb = repo.get_branch("main")
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sb.commit.sha)
    except Exception as e:
        return f"ブランチの作成に失敗しました: {str(e)}"

    prompt = f"""
    あなたは優秀なソフトウェア開発者です。以下のファイル群のコードを指示に基づいて修正してください。

    ファイル群：
    {chr(10).join([f"## ファイル名: {path}\n```python\n{content}\n```"
                   for path, content in files_content.items()])}

    指示：
    {message}

    以下のフォーマットで必ず構造的に回答してください（説明文なし）：

    {{
        "commit_message": "コミットの要約メッセージ",
        "changes": {{
            "file名1": "修正後のコード（変更がなければnull）",
            "file名2": "修正後のコード（変更がなければnull）"
        }},
        "explanation": "コミット内容の簡単な説明"
    }}
    """

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content
    except Exception as e:
        return f"GPTによる修正案の取得に失敗しました: {str(e)}"

    if result is None:
        return "GPTによる修正案の取得に失敗しました"

    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return "GPTのレスポンスをJSONに変換できませんでした。"

    commit_message = data.get("commit_message", "GPTによる自動修正")
    changes = data.get("changes", {})
    explanation = data.get("explanation", "")

    # 変更をコミット
    try:
        for file_name, new_code in changes.items():
            if new_code:
                file = get_file_from_repo(file_name)
                if file is None:
                    repo.create_file(
                        file_name, commit_message, new_code, branch=branch_name
                    )
                else:
                    repo.update_file(
                        file.path,
                        commit_message,
                        new_code,
                        file.sha,
                        branch=branch_name,
                    )
    except Exception as e:
        return f"GitHubへの変更の反映に失敗しました: {str(e)}"

    return f"GPTによる修正案をブランチ「{branch_name}」にpushしました。\n\nコミットの解説：{explanation}"
