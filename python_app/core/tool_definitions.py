from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType

TOOL_LAYOUTS = MappingProxyType(
    {
        "claude": MappingProxyType(
            {
                "label": "Claude",
                "root": (".claude",),
                "skills": (".claude", "skills"),
                "commands": (".claude", "commands"),
            }
        ),
        "codex": MappingProxyType(
            {
                "label": "Codex",
                "root": (".codex",),
                "skills": (".codex", "skills"),
                "commands": (".codex", "prompts"),
            }
        ),
        "gemini": MappingProxyType(
            {
                "label": "Gemini",
                "root": (".gemini",),
                "skills": (".gemini", "skills"),
                "commands": (".gemini", "commands"),
            }
        ),
        "antigravity": MappingProxyType(
            {
                "label": "Antigravity",
                "root": (".gemini", "antigravity"),
                "skills": (".gemini", "antigravity", "skills"),
                "commands": (".gemini", "antigravity", "global_workflows"),
            }
        ),
    }
)

TOOL_IDS = tuple(TOOL_LAYOUTS.keys())
TOOL_KIND_IDS = ("skills", "commands")
DEFAULT_COMMAND_SUBFOLDER_SUPPORT = {
    "default": False,
    "tools": {"claude": True},
}
DEFAULT_UPDATE_TOOLS = {
    "Claude Code": {"type": "custom", "command": "claude update"},
    "Codex": {"type": "npm", "package": "@openai/codex"},
    "OpenSpec": {"type": "npm", "package": "@fission-ai/openspec"},
    "Auggie": {"type": "npm", "package": "@augmentcode/auggie"},
    "ace-tool": {"type": "npm", "package": "ace-tool"},
}
DEFAULT_SYNC_MODE = "symlink"
CONFIG_VERSION = 2
WINDOWS_HOME_TOKEN = "%USERPROFILE%"
WSL_HOME_TOKEN = "$HOME"


def _join_segments(home_token: str, segments: tuple[str, ...], flavor: str) -> str:
    path_cls = PureWindowsPath if flavor == "windows" else PurePosixPath
    return str(path_cls(home_token, *segments))


def build_target_map(home_token: str, kind: str, flavor: str) -> dict[str, str]:
    return {
        tool_id: _join_segments(home_token, TOOL_LAYOUTS[tool_id][kind], flavor)
        for tool_id in TOOL_IDS
    }


def build_root_map(home_token: str, flavor: str) -> dict[str, str]:
    return {
        tool_id: _join_segments(home_token, TOOL_LAYOUTS[tool_id]["root"], flavor)
        for tool_id in TOOL_IDS
    }
