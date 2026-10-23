"""版本化 prompt：世界觀資料、資料區跳脫、messages 組裝。"""

from trpg.llm.prompts.builder import (
    PROMPT_VERSION,
    build_skill_proposal_messages,
    prompt_record,
    render_system_prompt,
)
from trpg.llm.prompts.escape import PLAYER_TEXT_MAX_CHARS, escape_text, wrap_player_input
from trpg.llm.prompts.world import WorldStyle, load_world_style

__all__ = [
    "PLAYER_TEXT_MAX_CHARS",
    "PROMPT_VERSION",
    "WorldStyle",
    "build_skill_proposal_messages",
    "escape_text",
    "load_world_style",
    "prompt_record",
    "render_system_prompt",
    "wrap_player_input",
]
