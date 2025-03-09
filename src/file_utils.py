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
