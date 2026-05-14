from datetime import timezone

from app.event_model import Mention, NormalizedEvent, ReplyTarget, Scene


class TestScene:
    def test_values(self) -> None:
        assert Scene.PRIVATE == "private"
        assert Scene.GROUP == "group"
        assert Scene.GUILD == "guild"
        assert Scene.CHANNEL == "channel"

    def test_membership(self) -> None:
        assert Scene.PRIVATE in Scene


class TestMention:
    def test_minimal(self) -> None:
        m = Mention(user_id="123")
        assert m.user_id == "123"
        assert m.display_name == ""

    def test_full(self) -> None:
        m = Mention(user_id="123", display_name="Alice")
        assert m.display_name == "Alice"


class TestNormalizedEvent:
    def test_minimal(self) -> None:
        event = NormalizedEvent(
            platform="qq",
            adapter="onebot_v11",
            scene=Scene.PRIVATE,
            chat_id="10001",
            user_id="12345",
            message_id="msg_001",
            text="hello",
        )
        assert event.platform == "qq"
        assert event.scene == Scene.PRIVATE
        assert event.text == "hello"
        assert event.mentions == ()
        assert event.reply_to is None
        assert event.timestamp.tzinfo is not None

    def test_frozen(self) -> None:
        event = NormalizedEvent(
            platform="qq",
            adapter="onebot_v11",
            scene=Scene.GROUP,
            chat_id="10001",
            user_id="12345",
            message_id="msg_001",
            text="hello",
        )
        import dataclasses
        assert dataclasses.fields(event)

    def test_with_mentions(self) -> None:
        mention = Mention(user_id="678", display_name="Bob")
        event = NormalizedEvent(
            platform="qq",
            adapter="onebot_v11",
            scene=Scene.GROUP,
            chat_id="10001",
            user_id="12345",
            message_id="msg_001",
            text="@Bob hello",
            mentions=(mention,),
        )
        assert len(event.mentions) == 1
        assert event.mentions[0].user_id == "678"

    def test_with_reply_to(self) -> None:
        event = NormalizedEvent(
            platform="qq",
            adapter="onebot_v11",
            scene=Scene.GROUP,
            chat_id="10001",
            user_id="12345",
            message_id="msg_001",
            text="reply test",
            reply_to="original_msg",
        )
        assert event.reply_to == "original_msg"


class TestReplyTarget:
    def test_private(self) -> None:
        target = ReplyTarget(scene=Scene.PRIVATE, chat_id="user_001", user_id="user_001")
        assert target.scene == Scene.PRIVATE
        assert target.chat_id == "user_001"

    def test_group(self) -> None:
        target = ReplyTarget(scene=Scene.GROUP, chat_id="group_001")
        assert target.scene == Scene.GROUP
        assert target.user_id is None
