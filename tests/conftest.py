from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.event_model import NormalizedEvent, Scene  # noqa: E402


def make_event(text: str, **overrides) -> NormalizedEvent:
    return NormalizedEvent(
        platform="test",
        adapter="test",
        scene=Scene.PRIVATE,
        chat_id="chat_001",
        user_id="user_001",
        message_id="msg_001",
        text=text,
        **overrides,
    )


class FakeSender:
    async def send_text(self, target, text: str) -> str:
        return "fake_id"

    async def send_reply(self, event, text: str) -> str:
        return "fake_id"
