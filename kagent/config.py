import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL", "gpt-5.4-mini")
DEFAULT_MODEL_OPTIONS = "gpt-5.5,gpt-5.4,gpt-5.4-mini,gpt-5.3-codex,gpt-5.2"
MODEL_OPTIONS = os.getenv("KAGENT_MODEL_OPTIONS", DEFAULT_MODEL_OPTIONS)
REASONING_EFFORT_OPTIONS = ["low", "medium", "high", "xhigh"]
REASONING_EFFORT = os.getenv("KAGENT_REASONING_EFFORT", "medium").strip().lower()
APP_LANGUAGE = os.getenv("APP_LANGUAGE", "zh").strip().lower()
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "kagent.db"))
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", str(BASE_DIR.parent))
STATE_DIR = os.getenv("KAGENT_STATE_DIR", str(BASE_DIR / ".kagent_state"))
ROLLBACK_ROOT = os.getenv("KAGENT_ROLLBACK_ROOT", str(Path(STATE_DIR) / "rollback"))
FILESYSTEM_READ_SCOPE = os.getenv("KAGENT_FS_READ_SCOPE", "all").strip().lower()
FILESYSTEM_WRITE_SCOPE = os.getenv("KAGENT_FS_WRITE_SCOPE", "workspace").strip().lower()
FILESYSTEM_COMMAND_SCOPE = os.getenv("KAGENT_FS_COMMAND_SCOPE", "workspace").strip().lower()
ALLOWED_WRITE_ROOTS = os.getenv("KAGENT_ALLOWED_WRITE_ROOTS", "")
ALLOWED_COMMAND_ROOTS = os.getenv("KAGENT_ALLOWED_COMMAND_ROOTS", "")
CONTEXT_MAX_TOKENS = int(os.getenv("KAGENT_CONTEXT_MAX_TOKENS", "24000"))
CONTEXT_KEEP_RECENT_MESSAGES = int(os.getenv("KAGENT_CONTEXT_KEEP_RECENT_MESSAGES", "24"))
CONTEXT_SUMMARY_MAX_CHARS = int(os.getenv("KAGENT_CONTEXT_SUMMARY_MAX_CHARS", "4000"))
CONTEXT_PER_MESSAGE_MAX_CHARS = int(os.getenv("KAGENT_CONTEXT_PER_MESSAGE_MAX_CHARS", "12000"))


def available_models() -> list[str]:
    values = [item.strip() for item in str(MODEL_OPTIONS or "").split(",") if item.strip()]
    if MODEL not in values:
        values.insert(0, MODEL)
    return list(dict.fromkeys(values))


def model_display_name(model: str) -> str:
    parts = str(model or "").strip().split("-")
    if not parts:
        return str(model or "")
    return "-".join(part.upper() if idx == 0 else part.capitalize() for idx, part in enumerate(parts))


def available_reasoning_efforts() -> list[str]:
    return list(REASONING_EFFORT_OPTIONS)


def normalize_reasoning_effort(effort: str | None) -> str:
    value = str(effort or "").strip().lower()
    if value in REASONING_EFFORT_OPTIONS:
        return value
    return "medium"


REASONING_EFFORT = normalize_reasoning_effort(REASONING_EFFORT)

SYSTEM_PROMPT = """你是 kagent，一个友好、专业的 AI 助手。

回答要求：
- 简洁清晰，必要时使用 Markdown 格式
- 代码块标注语言并附带简短说明
- 不确定时坦诚说明，不编造事实
"""

AGENT_SYSTEM_PROMPT = """你是 kagent，一个本地代码修改 agent，目标是帮用户在当前工作区完成工程任务。

工作区根目录：{workspace_root}

可用能力：
- read_file：读取工作区内的文本文件
- write_file：写回工作区内的文本文件
- list_files / search_file：查看目录结构、搜索代码与文本
- rename_path / copy_path / delete_path / make_directory：处理文件和目录操作
- run_command：在工作区内执行命令并查看输出

工作原则：
- 先阅读再修改，尽量只改和任务相关的文件
- 对代码类修改，先检查相关文件和项目结构，再落改动
- 修改后执行合理的验证命令，例如 Python 语法检查、测试或项目自带脚本
- 不要编造结果；如果命令失败，先看错误、继续修复，再重新验证
- 不要修改工作区外的文件
- 输出最终结果时，清楚说明改了什么、验证了什么、还有什么风险
"""
