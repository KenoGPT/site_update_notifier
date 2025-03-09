from github import Github
from github.ContentFile import ContentFile
import config

PAT = getattr(config, "PAT", "")
FORKED_REPO_NAME = getattr(config, "FORKED_REPO_NAME", "")


def get_file_from_repo(file_path: str, branch: str = "main") -> ContentFile | None:
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


def get_files_from_repo(
    file_path: str, branch: str = "main"
) -> list[ContentFile] | None:
    if not (PAT and FORKED_REPO_NAME):
        return None

    try:
        g = Github(PAT)
        repo = g.get_repo(FORKED_REPO_NAME)
        list = repo.get_contents(file_path, ref=branch)

        if isinstance(list, ContentFile):
            return None

        return list

    except Exception:
        return None


def get_all_file_paths(directory: str = "src", branch: str = "main") -> list[str]:
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
