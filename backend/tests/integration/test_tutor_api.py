"""Integration tests for tutor API endpoints and SSE stream."""

import asyncio
import uuid
from contextlib import aclosing
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.event_broadcaster import broadcaster
from app.db.repositories.tutor_repository import get_tutor_repository


@pytest.fixture
def stub_tutor_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub tutor workflow calls to avoid running LangGraph in tests."""

    async def fake_ainvoke(state: dict, config: dict | None = None) -> dict:
        return {"ok": True}

    async def fake_continue_workflow(session_id: uuid.UUID, state: dict, repo: object) -> None:
        return None

    monkeypatch.setattr(
        "app.api.v1.tutor.sessions.tutor_workflow.ainvoke",
        fake_ainvoke,
    )
    monkeypatch.setattr(
        "app.api.v1.tutor.messages.continue_workflow_after_message",
        fake_continue_workflow,
    )


@pytest.fixture
def fake_tutor_repo() -> object:
    """In-memory fake repo to avoid database dependency in tests."""

    class FakeSession(SimpleNamespace):
        id: uuid.UUID
        analysis_id: uuid.UUID | None
        status: str
        syllabus: dict[str, object] | None
        current_section: int
        current_lesson: int
        current_phase: str
        user_level: str
        understanding_scores: dict[str, float]
        conversation_summary: str | None
        session_metadata: dict[str, object] | None
        started_at: datetime
        completed_at: datetime | None

    class FakeMessage(SimpleNamespace):
        id: uuid.UUID
        session_id: uuid.UUID
        role: str
        content: str
        message_metadata: dict[str, object] | None
        created_at: datetime

    class FakeTutorRepo:
        def __init__(self) -> None:
            self.sessions: dict[uuid.UUID, FakeSession] = {}
            self.messages: dict[uuid.UUID, list[FakeMessage]] = {}

        async def create_session(
            self,
            analysis_id: uuid.UUID | None = None,
            user_level: str = "intermediate",
            session_metadata: dict[str, object] | None = None,
        ) -> FakeSession:
            session_id = uuid.uuid4()
            session = FakeSession(
                id=session_id,
                analysis_id=analysis_id,
                status="active",
                syllabus=None,
                current_section=0,
                current_lesson=0,
                current_phase="syllabus_generation",
                user_level=user_level,
                understanding_scores={},
                conversation_summary=None,
                session_metadata=session_metadata,
                started_at=datetime.now(UTC),
                completed_at=None,
            )
            self.sessions[session_id] = session
            self.messages[session_id] = []
            return session

        async def get_session(self, session_id: uuid.UUID) -> FakeSession | None:
            return self.sessions.get(session_id)

        async def get_session_with_messages(
            self, session_id: uuid.UUID
        ) -> tuple[FakeSession, list[FakeMessage]]:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            return session, list(self.messages.get(session_id, []))

        async def save_message(
            self,
            session_id: uuid.UUID,
            role: str,
            content: str,
            message_metadata: dict[str, object] | None = None,
        ) -> FakeMessage:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")
            message = FakeMessage(
                id=uuid.uuid4(),
                session_id=session_id,
                role=role,
                content=content,
                message_metadata=message_metadata,
                created_at=datetime.now(UTC),
            )
            self.messages[session_id].append(message)
            return message

        async def get_analysis_summary(self, analysis_id: uuid.UUID) -> dict[str, object] | None:
            return None

        async def update_session_state(
            self,
            session_id: uuid.UUID,
            syllabus: dict[str, object] | None = None,
            current_section: int | None = None,
            current_lesson: int | None = None,
            current_phase: str | None = None,
            understanding_scores: dict[str, float] | None = None,
            conversation_summary: str | None = None,
            status: str | None = None,
        ) -> FakeSession:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            if syllabus is not None:
                session.syllabus = syllabus
            if current_section is not None:
                session.current_section = current_section
            if current_lesson is not None:
                session.current_lesson = current_lesson
            if current_phase is not None:
                session.current_phase = current_phase
            if understanding_scores is not None:
                session.understanding_scores = understanding_scores
            if conversation_summary is not None:
                session.conversation_summary = conversation_summary
            if status is not None:
                session.status = status
            return session

    return FakeTutorRepo()


@pytest.fixture
async def async_client(fake_tutor_repo: object) -> AsyncClient:
    """Async HTTP client against the ASGI app."""
    app.dependency_overrides[get_tutor_repository] = lambda: fake_tutor_repo
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(get_tutor_repository, None)


@pytest.mark.asyncio
async def test_create_and_get_session(async_client: AsyncClient, stub_tutor_workflow: None) -> None:
    """Create a tutor session and fetch it."""
    create_resp = await async_client.post(
        "/api/v1/tutor/sessions",
        json={"analysis_id": None, "user_level": "beginner"},
    )
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    get_resp = await async_client.get(f"/api/v1/tutor/sessions/{session_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["session_id"] == session_id
    assert data["status"] == "active"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_send_message_and_stream(
    async_client: AsyncClient, stub_tutor_workflow: None
) -> None:
    """Send a message and observe SSE stream output."""
    create_resp = await async_client.post(
        "/api/v1/tutor/sessions",
        json={"analysis_id": None, "user_level": "intermediate"},
    )
    session_id = create_resp.json()["session_id"]

    send_resp = await async_client.post(
        f"/api/v1/tutor/sessions/{session_id}/messages",
        json={"content": "Hello tutor"},
    )
    assert send_resp.status_code == 200

    async def publish_events() -> None:
        await broadcaster.publish(
            f"tutor:{session_id}",
            {"type": "typing_start", "session_id": session_id},
        )
        await broadcaster.publish(
            f"tutor:{session_id}",
            {"type": "chunk", "session_id": session_id, "content": "Hi"},
        )
        await broadcaster.publish(
            f"tutor:{session_id}",
            {"type": "done", "session_id": session_id},
        )

    channel = f"tutor:{session_id}"
    events: list[dict[str, object]] = []
    async with aclosing(broadcaster.subscribe(channel)) as subscription:  # type: ignore[type-var]
        publish_task = asyncio.create_task(publish_events())
        for _ in range(3):
            event = await asyncio.wait_for(subscription.__anext__(), timeout=2.0)
            events.append(event)
        await publish_task

    types = {event.get("type") for event in events}
    assert {"typing_start", "chunk", "done"}.issubset(types)
