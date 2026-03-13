from __future__ import annotations

import io
import json
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_DEFAULT_TIMEOUT_SECONDS = 30
_GITHUB_HOSTS = {"github.com", "www.github.com"}
_USER_AGENT = "ai-config-sync"


@dataclass(frozen=True)
class GitHubTreeRef:
    owner: str
    repo: str
    ref: str
    path: str


def build_github_tree_url(source: GitHubTreeRef) -> str:
    base = f"https://github.com/{source.owner}/{source.repo}/tree/{source.ref}"
    normalized_path = str(PurePosixPath(source.path)) if source.path else ""
    if not normalized_path:
        return base
    return f"{base}/{normalized_path.strip('/')}"


def validate_skill_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("skill 名称不能为空。")
    if normalized.startswith("."):
        raise ValueError("skill 名称不能以 '.' 开头。")
    if any(sep in normalized for sep in ("/", "\\")):
        raise ValueError("skill 名称不能包含路径分隔符。")
    if Path(normalized).name != normalized:
        raise ValueError("skill 名称非法。")
    return normalized


def _http_get_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:
        raw = response.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"GitHub API 返回非 JSON：{url}") from error


def _http_get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:
        return response.read()


def _get_default_branch(owner: str, repo: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    data = _http_get_json(url)
    if not isinstance(data, dict):
        raise ValueError(f"GitHub API 返回异常：{url}")
    branch = str(data.get("default_branch") or "").strip()
    if not branch:
        raise ValueError(f"无法解析默认分支：{owner}/{repo}")
    return branch


def parse_github_tree_url(url: str) -> GitHubTreeRef:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL 不能为空。")
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL 必须以 http/https 开头。")
    if parsed.netloc not in _GITHUB_HOSTS:
        raise ValueError("暂仅支持 github.com 的 URL。")
    parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL 结构不正确（期望 owner/repo）。")
    owner = parts[0].strip()
    repo = parts[1].strip()
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        raise ValueError("GitHub URL 结构不正确（owner/repo 为空）。")

    ref = ""
    subpath = ""
    if len(parts) >= 4 and parts[2] == "tree":
        ref = parts[3].strip()
        subpath = "/".join(part for part in parts[4:] if part)
    else:
        ref = _get_default_branch(owner, repo)
        subpath = ""

    if not ref:
        raise ValueError("无法解析 GitHub ref（分支/标签/commit）。")
    return GitHubTreeRef(owner=owner, repo=repo, ref=ref, path=subpath)


def derive_child_tree_url(base_url: str, child_folder: str) -> str:
    base = parse_github_tree_url(base_url)
    child = validate_skill_name(child_folder)
    merged = str(PurePosixPath(base.path) / child) if base.path else child
    return build_github_tree_url(GitHubTreeRef(owner=base.owner, repo=base.repo, ref=base.ref, path=merged))


def get_latest_commit_sha(source: GitHubTreeRef) -> str:
    query: dict[str, str] = {"per_page": "1", "sha": source.ref}
    if source.path:
        query["path"] = source.path
    encoded = urllib.parse.urlencode(query, quote_via=urllib.parse.quote)
    url = f"https://api.github.com/repos/{source.owner}/{source.repo}/commits?{encoded}"
    data = _http_get_json(url)
    if not isinstance(data, list) or not data:
        raise ValueError(f"未找到 commits：{source.owner}/{source.repo} ({source.ref})")
    first = data[0]
    if not isinstance(first, dict):
        raise ValueError(f"GitHub API commits 返回异常：{url}")
    sha = str(first.get("sha") or "").strip()
    if not sha:
        raise ValueError(f"无法解析最新 commit sha：{url}")
    return sha


def _zip_root_prefix(zip_file: zipfile.ZipFile) -> str:
    names = [name for name in zip_file.namelist() if name and not name.endswith("/")]
    if not names:
        raise ValueError("zip 内容为空。")
    prefix = names[0].split("/", 1)[0].strip()
    if not prefix:
        raise ValueError("无法解析 zip 根目录。")
    return f"{prefix}/"


def _safe_member_relative_path(prefix: str, member_name: str) -> str:
    raw = member_name[len(prefix) :]
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"zip 条目路径非法：{member_name}")
    return str(candidate)


def _extract_zip_subpath(zip_bytes: bytes, subpath: str, dest_dir: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_file:
        root_prefix = _zip_root_prefix(zip_file)
        normalized_subpath = str(PurePosixPath(subpath)) if subpath else ""
        wanted_prefix = root_prefix + (normalized_subpath.strip("/") + "/" if normalized_subpath else "")
        members = [name for name in zip_file.namelist() if name.startswith(wanted_prefix) and name != wanted_prefix]
        if not members:
            raise ValueError(f"zip 中未找到路径：{subpath or '/'}")
        for member in members:
            if member.endswith("/"):
                continue
            relative = _safe_member_relative_path(wanted_prefix, member)
            target = dest_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with zip_file.open(member, "r") as source_fp:
                target.write_bytes(source_fp.read())


def install_github_tree_to_dir(source: GitHubTreeRef, dest_dir: Path) -> str:
    latest_sha = get_latest_commit_sha(source)
    zip_url = f"https://api.github.com/repos/{source.owner}/{source.repo}/zipball/{latest_sha}"
    try:
        zip_bytes = _http_get_bytes(zip_url)
    except urllib.error.HTTPError as error:
        raise ValueError(f"下载失败：{zip_url}（{error.code}）") from error

    with tempfile.TemporaryDirectory() as temp_dir:
        staging = Path(temp_dir) / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        _extract_zip_subpath(zip_bytes, source.path, staging)
        if dest_dir.exists():
            if dest_dir.is_dir():
                shutil.rmtree(dest_dir)
            else:
                dest_dir.unlink()
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging), str(dest_dir))
    return latest_sha
