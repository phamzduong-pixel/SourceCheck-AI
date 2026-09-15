"""Unit and Integration tests for Conversation and Message models (CHAT-02.1).

Covers:
- Creation of Conversation with default title and is_pinned
- Creation of Message with roles ('user', 'assistant') and extra_metadata (citations/evidence)
- Relationship navigation: User -> Conversation -> Message
- Multi-turn conversation message collection & ordering
- Cascade deletion behavior (Conversation delete -> Messages delete, User delete -> Conversations delete)
- Ownership constraint & isolation between users
- Alembic migration upgrade & downgrade SQL generation
- Pydantic schema validation & from_attributes conversion
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    MessageRole,
    MessageCreate,
    MessageRead,
    ConversationCreate,
    ConversationRead,
    ConversationSummary,
)


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite session with all models created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Creates a standard test user."""
    user = User(
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Nguyễn Văn Nghiên Cứu",
        role="researcher",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_conversation_defaults(db_session, test_user):
    """Verify Conversation creation with default title and is_pinned."""
    conversation = Conversation(user_id=test_user.id)
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    assert conversation.id is not None
    assert isinstance(conversation.id, uuid.UUID)
    assert conversation.user_id == test_user.id
    assert conversation.title == "Cuộc trò chuyện mới"
    assert conversation.is_pinned is False
    assert conversation.created_at is not None
    assert conversation.updated_at is not None


def test_create_conversation_custom_title_and_pinned(db_session, test_user):
    """Verify Conversation creation with custom title and pinned flag."""
    conversation = Conversation(
        user_id=test_user.id,
        title="Đối soát số liệu WTO 2007",
        is_pinned=True,
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    assert conversation.title == "Đối soát số liệu WTO 2007"
    assert conversation.is_pinned is True


def test_create_message_with_roles_and_metadata(db_session, test_user):
    """Verify Message creation with user & assistant roles and provenance extra_metadata."""
    conversation = Conversation(user_id=test_user.id, title="Tra cứu kinh tế số")
    db_session.add(conversation)
    db_session.commit()

    # 1. User message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content="Chiến lược kinh tế số Việt Nam đặt mục tiêu gì đến năm 2025?",
    )
    db_session.add(user_msg)

    # 2. Assistant message with rich grounding provenance metadata
    sample_metadata = {
        "status": "SUPPORTED",
        "evidence_coverage": 1.0,
        "verification_summary": {"SUPPORTED": 2, "REFUTED": 0, "NOT_ENOUGH_INFO": 0},
        "claims": [
            {
                "claim_id": "C1",
                "text": "Kinh tế số chiếm 20% GDP vào năm 2025.",
                "verdict": "SUPPORTED",
            }
        ],
        "citations": [
            {
                "citation_number": 1,
                "quote": "mục tiêu đến năm 2025 kinh tế số đạt 20% GDP",
                "source_title": "Quyết định 411/QĐ-TTg",
            }
        ],
    }
    ai_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="Theo Quyết định số 411/QĐ-TTg, mục tiêu kinh tế số chiếm 20% GDP vào năm 2025 [1].",
        extra_metadata=sample_metadata,
    )
    db_session.add(ai_msg)
    db_session.commit()

    db_session.refresh(user_msg)
    db_session.refresh(ai_msg)

    assert user_msg.id is not None
    assert user_msg.role == "user"
    assert "Chiến lược kinh tế số" in user_msg.content
    assert user_msg.conversation_id == conversation.id

    assert ai_msg.id is not None
    assert ai_msg.role == "assistant"
    assert ai_msg.extra_metadata["status"] == "SUPPORTED"
    assert ai_msg.extra_metadata["evidence_coverage"] == 1.0
    assert len(ai_msg.extra_metadata["citations"]) == 1
    assert ai_msg.extra_metadata["citations"][0]["citation_number"] == 1


def test_relationships_navigation(db_session, test_user):
    """Verify bidirectional ORM navigation: User <-> Conversation <-> Message."""
    conversation = Conversation(user_id=test_user.id, title="Kiểm định AI")
    msg1 = Message(conversation=conversation, role="user", content="Câu hỏi 1")
    msg2 = Message(conversation=conversation, role="assistant", content="Trả lời 1")

    db_session.add_all([conversation, msg1, msg2])
    db_session.commit()
    db_session.refresh(test_user)
    db_session.refresh(conversation)

    # User -> Conversations
    assert len(test_user.conversations) == 1
    assert test_user.conversations[0].id == conversation.id

    # Conversation -> User
    assert conversation.user.id == test_user.id
    assert conversation.user.email == test_user.email

    # Conversation -> Messages
    assert len(conversation.messages) == 2
    assert conversation.messages[0].content == "Câu hỏi 1"
    assert conversation.messages[1].content == "Trả lời 1"

    # Message -> Conversation
    assert msg1.conversation.id == conversation.id
    assert msg2.conversation.id == conversation.id


def test_conversation_multiple_messages_ordering(db_session, test_user):
    """Verify conversations can maintain multiple turns in chronological sequence."""
    conversation = Conversation(user_id=test_user.id, title="Multi-turn Dialogue")
    db_session.add(conversation)
    db_session.commit()

    turns = [
        ("user", "Chào bạn"),
        ("assistant", "Chào bạn, tôi là SourceCheck AI."),
        ("user", "WTO là gì?"),
        ("assistant", "WTO là Tổ chức Thương mại Thế giới [1]."),
        ("user", "Việt Nam gia nhập khi nào?"),
        ("assistant", "Việt Nam chính thức gia nhập ngày 11/01/2007 [2]."),
    ]

    for role, content in turns:
        msg = Message(conversation_id=conversation.id, role=role, content=content)
        db_session.add(msg)
    db_session.commit()
    db_session.refresh(conversation)

    assert len(conversation.messages) == 6
    for i, (expected_role, expected_content) in enumerate(turns):
        assert conversation.messages[i].role == expected_role
        assert conversation.messages[i].content == expected_content


def test_cascade_delete_conversation_removes_messages(db_session, test_user):
    """Verify deleting a Conversation cascades to remove all its Messages (no orphan messages)."""
    conversation = Conversation(user_id=test_user.id, title="Conversation to Delete")
    db_session.add(conversation)
    db_session.commit()

    msg1 = Message(conversation_id=conversation.id, role="user", content="Q1")
    msg2 = Message(conversation_id=conversation.id, role="assistant", content="A1")
    db_session.add_all([msg1, msg2])
    db_session.commit()

    conv_id = conversation.id
    msg1_id = msg1.id
    msg2_id = msg2.id

    # Verify messages exist
    stmt = select(Message).where(Message.conversation_id == conv_id)
    assert len(db_session.execute(stmt).scalars().all()) == 2

    # Delete Conversation
    db_session.delete(conversation)
    db_session.commit()

    # Verify Conversation is gone
    assert db_session.get(Conversation, conv_id) is None

    # Verify all child Messages are automatically cascaded and removed
    assert db_session.get(Message, msg1_id) is None
    assert db_session.get(Message, msg2_id) is None
    remaining_msgs = db_session.execute(select(Message).where(Message.conversation_id == conv_id)).scalars().all()
    assert len(remaining_msgs) == 0


def test_cascade_delete_user_removes_conversations_and_messages(db_session):
    """Verify deleting a User cascades to remove all their Conversations and Messages."""
    user = User(
        email=f"cascade_{uuid.uuid4().hex[:6]}@test.com",
        full_name="User to Delete",
        role="user",
    )
    db_session.add(user)
    db_session.commit()

    conversation = Conversation(user_id=user.id, title="User Conversation")
    db_session.add(conversation)
    db_session.commit()

    msg = Message(conversation_id=conversation.id, role="user", content="Hello")
    db_session.add(msg)
    db_session.commit()

    user_id = user.id
    conv_id = conversation.id
    msg_id = msg.id

    # Delete User
    db_session.delete(user)
    db_session.commit()

    # User, Conversation, and Message should all be deleted
    assert db_session.get(User, user_id) is None
    assert db_session.get(Conversation, conv_id) is None
    assert db_session.get(Message, msg_id) is None


def test_ownership_isolation(db_session):
    """Verify ownership separation: Conversations of User A belong only to User A."""
    user_a = User(email=f"a_{uuid.uuid4().hex[:6]}@test.com", full_name="User A", role="user")
    user_b = User(email=f"b_{uuid.uuid4().hex[:6]}@test.com", full_name="User B", role="user")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    conv_a1 = Conversation(user_id=user_a.id, title="Conversation A1")
    conv_a2 = Conversation(user_id=user_a.id, title="Conversation A2")
    conv_b1 = Conversation(user_id=user_b.id, title="Conversation B1")
    db_session.add_all([conv_a1, conv_a2, conv_b1])
    db_session.commit()

    # Query for User A
    stmt_a = select(Conversation).where(Conversation.user_id == user_a.id)
    user_a_convs = db_session.execute(stmt_a).scalars().all()
    assert len(user_a_convs) == 2
    assert {c.title for c in user_a_convs} == {"Conversation A1", "Conversation A2"}

    # Query for User B
    stmt_b = select(Conversation).where(Conversation.user_id == user_b.id)
    user_b_convs = db_session.execute(stmt_b).scalars().all()
    assert len(user_b_convs) == 1
    assert user_b_convs[0].title == "Conversation B1"

    # User B cannot claim User A's conversation
    assert conv_a1.user_id != user_b.id


def test_alembic_003_migration_upgrade_downgrade():
    """Verify Alembic migration 003 can execute upgrade and downgrade in offline SQL mode."""
    import alembic.config

    # Upgrade up to head (which includes 003)
    try:
        alembic.config.main(argv=["upgrade", "head", "--sql"])
    except Exception as exc:
        pytest.fail(f"Alembic upgrade head --sql failed: {exc}")

    # Downgrade 003 -> 002
    try:
        alembic.config.main(argv=["downgrade", "003_add_conversations_and_messages:002_add_google_oauth_to_users", "--sql"])
    except Exception as exc:
        pytest.fail(f"Alembic downgrade 003 -> 002 --sql failed: {exc}")


def test_pydantic_schema_validation(db_session, test_user):
    """Verify Pydantic schemas serialize and validate Conversation and Message models."""
    conversation = Conversation(user_id=test_user.id, title="Kiểm thử Pydantic")
    db_session.add(conversation)
    db_session.commit()

    msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="Đã xác thực",
        extra_metadata={"status": "SUPPORTED"},
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(conversation)
    db_session.refresh(msg)

    # 1. MessageRead from ORM
    msg_read = MessageRead.model_validate(msg)
    assert msg_read.id == msg.id
    assert msg_read.role == "assistant"
    assert msg_read.content == "Đã xác thực"
    assert msg_read.extra_metadata == {"status": "SUPPORTED"}

    # 2. ConversationRead from ORM with embedded messages
    conv_read = ConversationRead.model_validate(conversation)
    assert conv_read.id == conversation.id
    assert conv_read.title == "Kiểm thử Pydantic"
    assert len(conv_read.messages) == 1
    assert conv_read.messages[0].content == "Đã xác thực"

    # 3. ConversationSummary
    summary = ConversationSummary(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        is_pinned=conversation.is_pinned,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
    )
    assert summary.message_count == 1
    assert summary.title == "Kiểm thử Pydantic"
