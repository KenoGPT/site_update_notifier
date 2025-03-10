from github import Github
from github.ContentFile import ContentFile
from config import config

PAT = getattr(config, "PAT", "")
FORKED_REPO_NAME = getattr(config, "FORKED_REPO_NAME", "")
REPO_NAME = getattr(config, "REPO_NAME", "")


def get_file_from_repo(file_path: str, branch: str = "main") -> 
        ContentFile | None:
    """
    指定されたブランチから、
    FORKED_REPO_NAMEリポジトリ内のfile_pathの内容を取得する。
    成功時はContentFileオブジェクト、失敗時はNoneを返す。
    """
    if not (PAT and FORKED_REPO_NAME):
        return None
    try:
        g = Github(PAT)
        repo = g.get_repo(FORKED_REPO_NAME)
        content = repo.get_contents(file_path, ref=branch)
        if isinstance(content, list):
            return None
        return content
    except Exception:
        return None


def get_files_from_repo(file_path: str, branch: str = "main") -> 
        list[ContentFile] | None:
    """
    指定されたパスから、
    FORKED_REPO_NAMEリポジトリ内の全ファイルのContentFileリストを取得する。
    サブディレクトリは考慮されない。
    """
    if not (PAT and FORKED_REPO_NAME):
        return None
    try:
        g = Github(PAT)
        repo = g.get_repo(FORKED_REPO_NAME)
        contents = repo.get_contents(file_path, ref=branch)
        if isinstance(contents, ContentFile):
            return None
        return contents
    except Exception:
        return None


def get_all_file_paths(directory: str = "src", branch: str = "main") -> 
        list[str]:
    """
    指定ディレクトリ以下を再帰的に走査し、
    すべてのファイルパスのリストを返す。
    """
    contents = get_files_from_repo(directory, branch=branch)
    if contents is None:
        return []
    file_paths = []
    for content_file in contents:
        # サブディレクトリは再帰的に探索
        if content_file.type == "dir":
            file_paths += get_all_file_paths(content_file.path, branch)
        else:
            file_paths.append(content_file.path)
    return file_paths


def create_pull_request(branch_name: str, pr_title: str, pr_body: str = "") -> 
        str:
    """
    REPO_NAMEリポジトリに対して、
    FORKED_REPO_NAMEリポジトリからのブランチを基にプルリクエストを作成する。
    成功時はプルリク作成結果のメッセージを返す。
    """
    g = Github(PAT)
    try:
        base_repo = g.get_repo(REPO_NAME)
        forked_repo = g.get_repo(FORKED_REPO_NAME)
        pr = base_repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=f"{forked_repo.owner.login}:{branch_name}",
            base="main",
        )
        return f"プルリクエストが作成されました: {pr.html_url}"
    except Exception as e:
        return f"プルリクエストの作成に失敗しました: {str(e)}"
