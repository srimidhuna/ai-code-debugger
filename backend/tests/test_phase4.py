"""
Phase 4 backend tests:
- GET /api/history          (list, search, sort, pagination, filter)
- DELETE /api/history/{id}
- GET /api/settings/model
- GET /api/dashboard/stats
- Prompt contains the per-function / infinite-loop rule
- Existing Phase 2 sessions still work (GET, PATCH)
"""
import json
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models.session import SessionModel

from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Test database fixture (in-memory SQLite with StaticPool)
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def db_session(db_engine):
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestSession()
    yield session
    session.rollback()
    session.close()

@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_session(db, *, language="python", summary="Test session", decision="Pending",
                 issues=None, n_issues=0, timestamp=None):
    if issues is None:
        issues = [{"title": f"Issue {i}", "severity": "High", "category": "Logic",
                   "line": i+1, "line_end": i+1,
                   "explanation": "bug", "suggestion": "fix"} for i in range(n_issues)]
    s = SessionModel(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(timezone.utc),
        language=language,
        original_code="x = 1",
        fixed_code="x = 2",
        summary=summary,
        issues=issues,
        changes=[],
        remaining_concerns=[],
        decision=decision,
        model_name="test-model",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ===========================================================================
# GET /api/history
# ===========================================================================
class TestListHistory:
    def test_empty_database_returns_empty_list(self, client, db_session):
        # Clear table
        db_session.query(SessionModel).delete()
        db_session.commit()
        r = client.get("/api/history")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["sessions"] == []

    def test_lists_all_sessions(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        for _ in range(3):
            make_session(db_session)
        r = client.get("/api/history")
        assert r.status_code == 200
        assert r.json()["total"] == 3
        assert len(r.json()["sessions"]) == 3

    def test_search_by_summary(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        make_session(db_session, summary="null pointer error found")
        make_session(db_session, summary="stack overflow detected")
        r = client.get("/api/history?q=null+pointer")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert "null pointer" in body["sessions"][0]["summary"].lower()

    def test_filter_by_language(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        make_session(db_session, language="python")
        make_session(db_session, language="java")
        r = client.get("/api/history?language=python")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["sessions"][0]["language"] == "python"

    def test_filter_by_decision(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        make_session(db_session, decision="Accepted")
        make_session(db_session, decision="Rejected")
        make_session(db_session, decision="Pending")
        r = client.get("/api/history?decision=Accepted")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["sessions"][0]["decision"] == "Accepted"

    def test_pagination(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        for _ in range(5):
            make_session(db_session)
        r = client.get("/api/history?page=1&page_size=2")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 5
        assert len(body["sessions"]) == 2

        r2 = client.get("/api/history?page=3&page_size=2")
        assert r2.status_code == 200
        assert len(r2.json()["sessions"]) == 1

    def test_sort_asc(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        s1 = make_session(db_session, summary="older", timestamp=now - timedelta(hours=2))
        s2 = make_session(db_session, summary="newer", timestamp=now)
        r = client.get("/api/history?sort=asc")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["sessions"]]
        assert ids == [s1.id, s2.id]

    def test_sort_desc_default(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        s1 = make_session(db_session, summary="older", timestamp=now - timedelta(hours=2))
        s2 = make_session(db_session, summary="newer", timestamp=now)
        r = client.get("/api/history")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["sessions"]]
        assert ids == [s2.id, s1.id]


# ===========================================================================
# DELETE /api/history/{id}
# ===========================================================================
class TestDeleteSession:
    def test_delete_existing_session(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        s = make_session(db_session)
        r = client.delete(f"/api/history/{s.id}")
        assert r.status_code == 204
        # Confirm gone
        r2 = client.get(f"/api/history/{s.id}")
        assert r2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, db_session):
        r = client.delete(f"/api/history/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_delete_does_not_affect_other_sessions(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        s1 = make_session(db_session)
        s2 = make_session(db_session)
        client.delete(f"/api/history/{s1.id}")
        r = client.get(f"/api/history/{s2.id}")
        assert r.status_code == 200


# ===========================================================================
# GET /api/settings/model
# ===========================================================================
class TestSettingsModel:
    def test_returns_safe_model_info(self, client, db_session):
        r = client.get("/api/settings/model")
        assert r.status_code == 200
        body = r.json()
        assert "model" in body
        assert "timeout_seconds" in body
        assert "api_key_configured" in body
        assert "max_source_bytes" in body
        assert "max_source_lines" in body
        # Must not expose the raw API key
        assert "OPENROUTER_API_KEY" not in body
        assert "api_key" not in body or body.get("api_key") is None


# ===========================================================================
# GET /api/dashboard/stats
# ===========================================================================
class TestDashboardStats:
    def test_empty_database(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        r = client.get("/api/dashboard/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["total_sessions"] == 0
        assert body["total_issues"] == 0
        assert body["accepted_fixes"] == 0
        assert body["rejected_fixes"] == 0
        assert body["recent_sessions"] == []

    def test_stats_match_database(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        make_session(db_session, decision="Accepted", n_issues=2)
        make_session(db_session, decision="Rejected", n_issues=1)
        make_session(db_session, decision="Pending",  n_issues=3)

        r = client.get("/api/dashboard/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["total_sessions"] == 3
        assert body["total_issues"] == 6
        assert body["accepted_fixes"] == 1
        assert body["rejected_fixes"] == 1

    def test_recent_sessions_max_five(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        for _ in range(7):
            make_session(db_session)
        r = client.get("/api/dashboard/stats")
        assert r.status_code == 200
        assert len(r.json()["recent_sessions"]) == 5

    def test_recent_sessions_no_source_code(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        make_session(db_session)
        r = client.get("/api/dashboard/stats")
        body = r.json()
        if body["recent_sessions"]:
            recent = body["recent_sessions"][0]
            assert "original_code" not in recent
            assert "fixed_code" not in recent

    def test_persistence_across_calls(self, client, db_session):
        """Two consecutive calls return the same statistics."""
        db_session.query(SessionModel).delete()
        db_session.commit()
        make_session(db_session, decision="Accepted")
        r1 = client.get("/api/dashboard/stats")
        r2 = client.get("/api/dashboard/stats")
        assert r1.json() == r2.json()


# ===========================================================================
# Prompt rule: check every function + infinite-loop detection
# ===========================================================================
class TestPromptContainsPerFunctionRule:
    def test_prompt_has_per_function_check_rule(self):
        """The analysis prompt must instruct the model to check every function
        separately and report infinite loops (while loops with no update) as issues.
        """
        from app.services.debugging_service import DebuggingService

        svc = DebuggingService.__new__(DebuggingService)
        messages = svc._build_initial_messages(
            code="def foo():\n    x = 0\n    while True:\n        pass\n",
            language="python",
            numbered_code="1: def foo():\n2:     x = 0\n3:     while True:\n4:         pass",
            total_lines=4,
        )
        system_content = messages[0]["content"]
        # Must mention checking each function separately
        assert "every function" in system_content
        # Must mention loops that never terminate / condition variable not updated
        assert "while" in system_content.lower() or "never terminate" in system_content.lower()
        assert "condition variable" in system_content or "never updated" in system_content


# ===========================================================================
# Existing Phase 2 endpoints still work (regression)
# ===========================================================================
class TestPhase2Regression:
    def test_get_session_existing(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        s = make_session(db_session)
        r = client.get(f"/api/history/{s.id}")
        assert r.status_code == 200
        assert r.json()["id"] == s.id

    def test_get_session_missing(self, client, db_session):
        r = client.get(f"/api/history/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_patch_session_accepted(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        s = make_session(db_session)
        r = client.patch(f"/api/history/{s.id}", json={"decision": "Accepted"})
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "Accepted"
        assert body["original_code"] == "x = 1"
        assert body["fixed_code"] == "x = 2"

    def test_patch_session_rejected(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        s = make_session(db_session)
        r = client.patch(f"/api/history/{s.id}", json={"decision": "Rejected"})
        assert r.status_code == 200
        assert r.json()["decision"] == "Rejected"

    def test_patch_invalid_decision(self, client, db_session):
        db_session.query(SessionModel).delete()
        db_session.commit()
        s = make_session(db_session)
        r = client.patch(f"/api/history/{s.id}", json={"decision": "Maybe"})
        assert r.status_code == 422


# ===========================================================================
# Persistence across restarts & Database failure handling
# ===========================================================================
class TestPersistenceAcrossRestart:
    def test_persistence_across_restarts_on_sqlite_file(self, tmp_path):
        """Simulate an actual backend restart:
        Create a session with one engine/session on a SQLite file,
        dispose/close all connections, then instantiate a brand new engine
        and session on the exact same SQLite file and verify data persists.
        """
        db_file = tmp_path / "restart_test.db"
        file_db_url = f"sqlite:///{db_file}"

        # 1. First run / instance
        engine1 = create_engine(file_db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine1)
        Session1 = sessionmaker(bind=engine1)
        s1 = Session1()

        created = SessionModel(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            language="python",
            original_code="print('hello')",
            fixed_code="print('hello world')",
            summary="Fixed greeting",
            issues=[{"title": "Missing world", "severity": "Low", "category": "Quality",
                     "line": 1, "line_end": 1, "explanation": "greeting incomplete", "suggestion": "add world"}],
            changes=[{"description": "added world", "reason": "more complete"}],
            remaining_concerns=[],
            decision="Accepted",
            model_name="test-model",
        )
        s1.add(created)
        s1.commit()
        created_id = created.id
        s1.close()
        engine1.dispose()

        # 2. Simulated restart: completely new engine and session on the same file
        engine2 = create_engine(file_db_url, connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        s2 = Session2()

        loaded = s2.query(SessionModel).filter(SessionModel.id == created_id).first()
        assert loaded is not None
        assert loaded.id == created_id
        assert loaded.summary == "Fixed greeting"
        assert loaded.decision == "Accepted"
        assert loaded.original_code == "print('hello')"
        assert loaded.fixed_code == "print('hello world')"
        assert len(loaded.issues) == 1

        s2.close()
        engine2.dispose()


class TestDatabaseFailureHandling:
    def test_failed_patch_decision_returns_clear_error(self, client, db_session):
        """When a database commit fails during decision update, the endpoint rolls back
        and returns a 500 error with a clear database error message."""
        s = make_session(db_session)
        with pytest.MonkeyPatch.context() as mp:
            from sqlalchemy.orm import Session
            def fake_commit(self):
                raise Exception("Simulated disk I/O error during commit")
            mp.setattr(Session, "commit", fake_commit)

            r = client.patch(f"/api/history/{s.id}", json={"decision": "Accepted"})
            assert r.status_code == 500
            body = r.json()
            assert "detail" in body
            assert "database error" in body["detail"].lower()
            assert "simulated disk i/o error" in body["detail"].lower()

    def test_failed_delete_returns_clear_error(self, client, db_session):
        """When a database commit fails during delete, a 500 error is returned with a clear message."""
        s = make_session(db_session)
        with pytest.MonkeyPatch.context() as mp:
            from sqlalchemy.orm import Session
            def fake_commit(self):
                raise Exception("Simulated database lock failure")
            mp.setattr(Session, "commit", fake_commit)

            r = client.delete(f"/api/history/{s.id}")
            assert r.status_code == 500
            body = r.json()
            assert "detail" in body
            assert "database error" in body["detail"].lower()
            assert "simulated database lock" in body["detail"].lower()

