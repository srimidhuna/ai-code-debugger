import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.session import SessionModel
from app.core.exceptions import (
    OpenRouterAuthError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
    OpenRouterNetworkError,
    OpenRouterConfigError,
    AIValidationError,
)
from app.services.debugging_service import (
    extract_json_from_text,
    extract_edits_from_text,
    validate_and_apply_edits,
    CodeEdit,
    MAX_EDITS_PER_REQUEST,
)

# ─── In-memory SQLite for tests ──────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ─── Helpers for building valid model replies ─────────────────────────────────
METADATA_DICT = {
    "summary": "Fixed a syntax error and an infinite loop logic issue.",
    "issues": [
        {
            "title": "Missing Colon",
            "severity": "Critical",
            "category": "Syntax",
            "line": 1,
            "line_end": 1,
            "explanation": "Function definition requires a trailing colon.",
            "suggestion": "Add ':' at end of line 1."
        }
    ],
    "changes": [
        {"description": "Added missing colon", "reason": "Python syntax requirement"}
    ],
    "remaining_concerns": []
}

def make_valid_reply(metadata: dict = None, edits: list = None) -> str:
    """Build the two-part format the service expects: JSON metadata followed by <edit> blocks."""
    m = metadata if metadata is not None else METADATA_DICT
    json_part = json.dumps(m)
    if edits is None:
        # Default single-line edit replacing line 1: "def solve():"
        edits = [
            '<edit start="1" end="1">\n<replacement>\ndef solve():\n</replacement>\n</edit>'
        ]
    edits_part = "\n\n".join(edits)
    return f"{json_part}\n\n{edits_part}"

# ─── Unit tests: extract_json_from_text ──────────────────────────────────────

def test_extract_plain_json():
    raw = '{"summary": "ok", "issues": [], "changes": [], "remaining_concerns": []}'
    result = extract_json_from_text(raw)
    assert result["summary"] == "ok"

def test_extract_fenced_json():
    raw = '```json\n{"summary": "fenced", "issues": []}\n```'
    result = extract_json_from_text(raw)
    assert result["summary"] == "fenced"

def test_extract_plain_fenced_json():
    raw = '```\n{"summary": "plain fence"}\n```'
    result = extract_json_from_text(raw)
    assert result["summary"] == "plain fence"

def test_extract_trailing_commas():
    raw = '{"summary": "tc", "issues": [], "changes": [], "remaining_concerns": [],}'
    result = extract_json_from_text(raw)
    assert result["summary"] == "tc"

def test_extract_trailing_comma_in_array():
    raw = '{"summary": "arr", "issues": [{"a": 1},], "changes": [], "remaining_concerns": []}'
    result = extract_json_from_text(raw)
    assert result["summary"] == "arr"

def test_extract_unquoted_key():
    # Simulate bare key 'title'
    raw = '{"summary": "uq", issues: [], "changes": [], "remaining_concerns": []}'
    result = extract_json_from_text(raw)
    assert result["summary"] == "uq"

def test_extract_json_with_surrounding_prose():
    raw = 'Here is the analysis:\n{"summary": "prose", "issues": []}\nDone.'
    result = extract_json_from_text(raw)
    assert result["summary"] == "prose"

def test_extract_json_with_unescaped_inner_quotes():
    raw = '{"summary": "test", "issues": [{"title": "t", "explanation": "The variable "max_val" is wrong"}], "changes": [], "remaining_concerns": []}'
    result = extract_json_from_text(raw)
    assert result["summary"] == "test"
    assert len(result["issues"]) == 1

def test_extract_json_with_missing_comma_delimiter():
    raw = '{"summary": "test" "issues": [{"title": "t" "category": "Logic"}] "changes": [] "remaining_concerns": []}'
    result = extract_json_from_text(raw)
    assert result["summary"] == "test"
    assert len(result["issues"]) == 1


# ─── Unit tests: extract_edits_from_text & validate_and_apply_edits ─────────

def test_extract_edits_from_text_multiple():
    text = (
        '{"summary": "test"}\n\n'
        '<edit start="2" end="2">\n'
        '<replacement>\n'
        '    count = 0\n'
        '</replacement>\n'
        '</edit>\n\n'
        '<edit start="5" end="4">\n'
        '<replacement>\n'
        '    # inserted comment\n'
        '</replacement>\n'
        '</edit>'
    )
    edits, remainder = extract_edits_from_text(text)
    assert len(edits) == 2
    assert edits[0].start_line == 2
    assert edits[0].end_line == 2
    assert edits[0].replacement_text == "    count = 0"
    assert edits[1].start_line == 5
    assert edits[1].end_line == 4
    assert edits[1].replacement_text == "    # inserted comment"
    assert "<edit" not in remainder
    assert "</edit>" not in remainder


# Required Test 1: Single-line fix
def test_patch_single_line_fix():
    orig = "def foo()\n    return 42\n"
    edits = [
        CodeEdit(start_line=1, end_line=1, replacement_text="def foo():")
    ]
    fixed = validate_and_apply_edits(orig, edits, total_lines=2)
    assert fixed == "def foo():\n    return 42\n"


# Required Test 2: Multi-line replacement
def test_patch_multi_line_replacement():
    orig = "def compute(x):\n    a = 1\n    b = 2\n    return a + b\n"
    edits = [
        CodeEdit(start_line=2, end_line=3, replacement_text="    # direct return\n    return x * 2")
    ]
    fixed = validate_and_apply_edits(orig, edits, total_lines=4)
    expected = "def compute(x):\n    # direct return\n    return x * 2\n    return a + b\n"
    assert fixed == expected


# Required Test 3: Insertion (convention: end_line = start_line - 1)
def test_patch_insertion_convention():
    orig = "def solve():\n    return 42\n"
    # Insert before line 2 (start=2, end=1)
    edits = [
        CodeEdit(start_line=2, end_line=1, replacement_text="    # calculation note")
    ]
    fixed = validate_and_apply_edits(orig, edits, total_lines=2)
    assert fixed == "def solve():\n    # calculation note\n    return 42\n"


# Required Test 4: Deletion (empty replacement)
def test_patch_deletion():
    orig = "def solve():\n    unused_debug_print()\n    return 42\n"
    edits = [
        CodeEdit(start_line=2, end_line=2, replacement_text="")
    ]
    fixed = validate_and_apply_edits(orig, edits, total_lines=3)
    assert fixed == "def solve():\n    return 42\n"


# Required Test 5: Overlapping edits rejected
def test_patch_overlapping_edits_rejected():
    orig = "line 1\nline 2\nline 3\nline 4\n"
    edits = [
        CodeEdit(start_line=1, end_line=3, replacement_text="new 1-3"),
        CodeEdit(start_line=2, end_line=4, replacement_text="new 2-4"),
    ]
    with pytest.raises(AIValidationError) as exc:
        validate_and_apply_edits(orig, edits, total_lines=4)
    assert "overlapping" in str(exc.value).lower()


# Required Test 6: Out-of-range rejected
def test_patch_out_of_range_rejected():
    orig = "line 1\nline 2\n"
    # start_line=5 exceeds total_lines=2
    edits = [
        CodeEdit(start_line=5, end_line=5, replacement_text="out of range")
    ]
    with pytest.raises(AIValidationError) as exc:
        validate_and_apply_edits(orig, edits, total_lines=2)
    assert "invalid edit range" in str(exc.value).lower() or "bounds" in str(exc.value).lower()

    # negative or 0 line
    edits_zero = [CodeEdit(start_line=0, end_line=1, replacement_text="zero")]
    with pytest.raises(AIValidationError):
        validate_and_apply_edits(orig, edits_zero, total_lines=2)


# Required Test 7: Untouched lines unchanged byte for byte
def test_patch_untouched_lines_unchanged_byte_for_byte():
    orig = (
        "def average(numbers):\n"
        "    total = 0\n"
        "    for n in numbers:\n"
        "        total += n\n"
        "    return total / len(numbers)\n"
        "\n"
        "def count_even(numbers):\n"
        "    count = 0\n"
        "    for i in range(len(numbers)):\n"
        "        if numbers[i] % 2 == 0:\n"
        "            count += 1\n"
        "    return count\n"
    )
    # Edit only inside count_even (lines 10-10)
    edits = [
        CodeEdit(start_line=10, end_line=10, replacement_text="        if numbers[i] % 2 == 0:  # checked")
    ]
    fixed = validate_and_apply_edits(orig, edits, total_lines=12)
    # The entire average function and all preceding lines must match byte-for-byte
    avg_block = (
        "def average(numbers):\n"
        "    total = 0\n"
        "    for n in numbers:\n"
        "        total += n\n"
        "    return total / len(numbers)\n"
        "\n"
        "def count_even(numbers):\n"
        "    count = 0\n"
        "    for i in range(len(numbers)):\n"
    )
    assert fixed.startswith(avg_block)
    assert "        if numbers[i] % 2 == 0:  # checked\n" in fixed
    assert fixed.endswith("    return count\n")


# Required Test 8: Trailing newline preserved
def test_patch_trailing_newline_preserved():
    # Case A: Has trailing newline
    orig_with_newline = "a = 1\nb = 2\n"
    edits = [CodeEdit(start_line=1, end_line=1, replacement_text="a = 10")]
    fixed_with = validate_and_apply_edits(orig_with_newline, edits, total_lines=2)
    assert fixed_with.endswith("\n")
    assert fixed_with == "a = 10\nb = 2\n"

    # Case B: No trailing newline
    orig_no_newline = "a = 1\nb = 2"
    fixed_no = validate_and_apply_edits(orig_no_newline, edits, total_lines=2)
    assert not fixed_no.endswith("\n")
    assert fixed_no == "a = 10\nb = 2"


# Required Test 9: CRLF input handling
def test_patch_crlf_input_handling():
    orig_crlf = "def f():\r\n    a = 1\r\n    return a\r\n"
    edits = [CodeEdit(start_line=2, end_line=2, replacement_text="    a = 2")]
    fixed = validate_and_apply_edits(orig_crlf, edits, total_lines=3)
    assert "\r\n" in fixed
    assert fixed == "def f():\r\n    a = 2\r\n    return a\r\n"


# Required Test 10: Edit producing invalid Python rejected via ast.parse
def test_validate_fixed_code_safety_python_ast_parse():
    """Verify that Python code with syntax errors fails ast.parse compilation check."""
    from app.services.debugging_service import DebuggingService
    service = DebuggingService.__new__(DebuggingService)

    orig = "def solve():\n    return 42\n"
    bad_syntax = "def solve():\n    return 42 +\n"

    with pytest.raises(AIValidationError) as exc:
        service._validate_fixed_code_safety(orig, bad_syntax, "python")
    assert "syntax error" in str(exc.value).lower()


def test_validate_fixed_code_safety_catches_collapsed_lines():
    from app.services.debugging_service import DebuggingService
    service = DebuggingService.__new__(DebuggingService)

    orig = (
        "def average(numbers):\n"
        "    total = 0\n"
        "    for n in numbers:\n"
        "        total += n\n"
        "    return total / len(numbers)\n"
        "\n"
        "def count_even(numbers):\n"
        "    count = 0\n"
        "    for i in range(len(numbers) + 1):\n"
        "        if numbers[i] % 2 == 0:\n"
        "            count += 1\n"
        "    return count\n"
    )

    # Collapsed version missing line breaks
    collapsed = (
        "def average(numbers):\n"
        "    total =0    for n in numbers:\n"
        "        total += n\n"
        "    return total / len(numbers)\n"
        "def count_even(numbers):\n"
        "    count =0    for i in range(len(numbers)):\n"
        "        if numbers[i] % 2 == 0:\n"
        "            count += 1return count\n"
    )

    with pytest.raises(AIValidationError) as exc:
        service._validate_fixed_code_safety(orig, collapsed, "python")
    assert "safety validation" in str(exc.value)


def test_validate_fixed_code_safety_cpp_abnormal_whitespace():
    """Verify that other languages (C++, Java) trigger error on abnormal whitespace runs."""
    from app.services.debugging_service import DebuggingService
    service = DebuggingService.__new__(DebuggingService)

    orig = "int add(int a, int b) {\n    return a + b;\n}\nint sub(int a, int b) {\n    return a - b;\n}\n"
    collapsed_cpp = "int add(int a, int b) {\n    return a + b;    int sub(int a, int b) {\n    return a - b;\n}\n"

    with pytest.raises(AIValidationError) as exc:
        service._validate_fixed_code_safety(orig, collapsed_cpp, "cpp")
    assert "safety validation" in str(exc.value)

# ─── Integration tests: database ─────────────────────────────────────────────


def test_database_initialization():
    assert "debugging_sessions" in Base.metadata.tables

# ─── Integration tests: POST /api/debug ──────────────────────────────────────

@pytest.mark.asyncio
async def test_successful_analysis_creates_pending_session():
    mock_generate = AsyncMock(return_value=make_valid_reply())
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post(
            "/api/debug",
            json={"code": "def solve()\n    return 42\n", "language": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "Pending"
        assert data["language"] == "python"
        assert data["summary"] == METADATA_DICT["summary"]
        assert len(data["issues"]) == 1
        assert data["issues"][0]["severity"] == "Critical"
        assert data["fixed_code"] == "def solve():\n    return 42\n"
        assert "id" in data

        db = TestingSessionLocal()
        saved = db.query(SessionModel).filter(SessionModel.id == data["id"]).first()
        assert saved is not None
        assert saved.decision == "Pending"
        assert saved.original_code == "def solve()\n    return 42\n"
        assert saved.fixed_code == "def solve():\n    return 42\n"
        db.close()

def test_empty_code_rejected():
    response = client.post("/api/debug", json={"code": "   ", "language": "python"})
    assert response.status_code == 422

def test_unsupported_language_rejected():
    response = client.post("/api/debug", json={"code": "println!(\"hi\")", "language": "rust"})
    assert response.status_code == 422

def test_input_exceeding_max_bytes():
    oversized_code = "a = 1\n" * 20000
    assert len(oversized_code.encode("utf-8")) > 102400
    response = client.post("/api/debug", json={"code": oversized_code, "language": "python"})
    assert response.status_code == 413

def test_input_exceeding_max_lines():
    too_many_lines = "\n".join(["x = 1"] * 3005)
    response = client.post("/api/debug", json={"code": too_many_lines, "language": "python"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_invalid_json_retry_exhaustion():
    """Both attempts return invalid JSON → 502, exactly 2 calls."""
    mock_generate = AsyncMock(return_value="This is not valid at all!")
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 502
        assert "failed schema validation" in response.json()["detail"].lower()
        assert mock_generate.call_count == 2

@pytest.mark.asyncio
async def test_invalid_edits_retry_exhaustion():
    """Model returns out-of-range edits on both attempts → retry, still fails → 502."""
    bad_reply = (
        '{"summary": "x", "issues": [], "changes": [], "remaining_concerns": []}\n\n'
        '<edit start="999" end="999"><replacement>x</replacement></edit>'
    )
    mock_generate = AsyncMock(return_value=bad_reply)
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 502
        assert mock_generate.call_count == 2

@pytest.mark.asyncio
async def test_successful_bounded_retry():
    """First attempt fails, second succeeds → 200, exactly 2 calls."""
    first_attempt = "Not valid"
    second_attempt = make_valid_reply()
    mock_generate = AsyncMock(side_effect=[first_attempt, second_attempt])
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post(
            "/api/debug",
            json={"code": "def solve()\n    return 42\n", "language": "python"},
        )
        assert response.status_code == 200
        assert mock_generate.call_count == 2
        assert response.json()["decision"] == "Pending"
        assert response.json()["fixed_code"] == "def solve():\n    return 42\n"

@pytest.mark.asyncio
async def test_fenced_json_in_reply():
    """Model wraps metadata in ```json fences — must parse successfully."""
    fenced = (
        f"```json\n{json.dumps(METADATA_DICT)}\n```\n\n"
        '<edit start="1" end="1">\n<replacement>\ndef solve():\n</replacement>\n</edit>'
    )
    mock_generate = AsyncMock(return_value=fenced)
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "def solve()\n    return 42\n", "language": "python"})
        assert response.status_code == 200
        assert response.json()["fixed_code"] == "def solve():\n    return 42\n"

@pytest.mark.asyncio
async def test_trailing_commas_in_reply():
    """Model emits trailing commas in JSON — must parse successfully."""
    trailing = (
        '{"summary": "tc", "issues": [], "changes": [], "remaining_concerns": [],}'
        '\n\n<edit start="1" end="1">\n<replacement>\ndef solve():\n</replacement>\n</edit>'
    )
    mock_generate = AsyncMock(return_value=trailing)
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "def solve()\n    return 42\n", "language": "python"})
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_multiline_edit_in_delimited_block():
    """Multi-line replacement with backslashes and special chars round-trips intact."""
    multiline_edit = [
        '<edit start="1" end="1">\n<replacement>\nprintf("%d\\n", x);\nreturn 0;\n</replacement>\n</edit>'
    ]
    reply = make_valid_reply(edits=multiline_edit)
    mock_generate = AsyncMock(return_value=reply)
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "printf(\"%d\", x);\n", "language": "c"})
        assert response.status_code == 200
        assert response.json()["fixed_code"] == 'printf("%d\\n", x);\nreturn 0;\n'


# ─── Error mapping tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authentication_error_returns_502():
    mock_generate = AsyncMock(side_effect=OpenRouterAuthError())
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 502

@pytest.mark.asyncio
async def test_config_error_returns_503():
    mock_generate = AsyncMock(side_effect=OpenRouterConfigError())
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 503

@pytest.mark.asyncio
async def test_rate_limit_error_returns_429():
    mock_generate = AsyncMock(side_effect=OpenRouterRateLimitError())
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 429

@pytest.mark.asyncio
async def test_timeout_error_returns_504():
    mock_generate = AsyncMock(side_effect=OpenRouterTimeoutError())
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 504

@pytest.mark.asyncio
async def test_network_failure_returns_502():
    mock_generate = AsyncMock(side_effect=OpenRouterNetworkError("DNS lookup failed"))
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 502

@pytest.mark.asyncio
async def test_failed_analysis_does_not_persist_session():
    db = TestingSessionLocal()
    initial_count = db.query(SessionModel).count()
    db.close()
    mock_generate = AsyncMock(side_effect=OpenRouterTimeoutError())
    with patch("app.services.openrouter_client.OpenRouterClient.generate_chat_completion", mock_generate):
        response = client.post("/api/debug", json={"code": "print(1)", "language": "python"})
        assert response.status_code == 504
        db = TestingSessionLocal()
        assert db.query(SessionModel).count() == initial_count
        db.close()

# ─── History endpoint tests ───────────────────────────────────────────────────

def _create_session_in_db(**kwargs) -> str:
    db = TestingSessionLocal()
    defaults = dict(
        id=str(uuid.uuid4()),
        language="python",
        original_code="print('bug')",
        fixed_code="print('fixed')",
        summary="Fixed bug",
        issues=[],
        changes=[],
        remaining_concerns=[],
        decision="Pending",
        model_name="qwen/qwen-2.5-coder-32b-instruct",
    )
    defaults.update(kwargs)
    session = SessionModel(**defaults)
    db.add(session)
    db.commit()
    session_id = session.id
    db.close()
    return session_id

def test_get_existing_session():
    session_id = _create_session_in_db()
    response = client.get(f"/api/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["decision"] == "Pending"

def test_get_nonexistent_session_returns_404():
    response = client.get(f"/api/history/{uuid.uuid4()}")
    assert response.status_code == 404

def test_update_session_to_accepted():
    session_id = _create_session_in_db(
        original_code="orig_code()",
        fixed_code="fixed_code()",
        summary="Summary test",
        issues=[{"title": "Issue 1", "severity": "High", "category": "Logic",
                 "explanation": "e", "suggestion": "s"}],
    )
    response = client.patch(f"/api/history/{session_id}", json={"decision": "Accepted"})
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "Accepted"
    assert data["original_code"] == "orig_code()"
    assert data["fixed_code"] == "fixed_code()"
    assert data["summary"] == "Summary test"
    assert len(data["issues"]) == 1

def test_update_session_to_rejected():
    session_id = _create_session_in_db(language="javascript",
                                        original_code="const x = 1;",
                                        fixed_code="const x = 2;")
    response = client.patch(f"/api/history/{session_id}", json={"decision": "Rejected"})
    assert response.status_code == 200
    assert response.json()["decision"] == "Rejected"
    assert response.json()["original_code"] == "const x = 1;"
    assert response.json()["fixed_code"] == "const x = 2;"

def test_invalid_decision_value_returns_422():
    response = client.patch(f"/api/history/{uuid.uuid4()}", json={"decision": "Maybe"})
    assert response.status_code == 422

def test_update_nonexistent_session_returns_404():
    response = client.patch(f"/api/history/{uuid.uuid4()}", json={"decision": "Accepted"})
    assert response.status_code == 404

def test_decision_update_preserves_source_and_analysis():
    session_id = _create_session_in_db(
        language="c",
        original_code="int main() { return 0; }",
        fixed_code="int main(void) { return 0; }",
        summary="C syntax fix",
    )
    response = client.patch(f"/api/history/{session_id}", json={"decision": "Accepted"})
    assert response.status_code == 200

    db = TestingSessionLocal()
    saved = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    assert saved.decision == "Accepted"
    assert saved.original_code == "int main() { return 0; }"
    assert saved.fixed_code == "int main(void) { return 0; }"
    assert saved.summary == "C syntax fix"
    db.close()


# ─── Prompt content tests ─────────────────────────────────────────────────────

def test_prompt_contains_required_behavioural_rules():
    """Verify the system prompt enforces all four new behavioural rules.

    Rules under test:
    R1 – Describe actual original behaviour (not assumed exceptions/failures).
    R2 – No new behaviour added beyond fixing the reported bug.
    R3 – Each distinct bug is its own issue with its own line.
    R4 – Specific line numbers or tight ranges, not whole-function ranges.
    """
    from app.services.debugging_service import DebuggingService

    service = DebuggingService.__new__(DebuggingService)
    sample_code = "def f():\n    return 1\n"
    numbered, total = "1: def f():\n2:     return 1", 2
    messages = service._build_initial_messages(sample_code, "python", numbered, total)

    assert len(messages) == 2
    system_content = messages[0]["content"]
    assert messages[0]["role"] == "system"

    # R1: must instruct model to describe what the ORIGINAL code actually does,
    #     and not claim an exception unless provably raised.
    assert "ORIGINAL code" in system_content, \
        "System prompt must reference 'ORIGINAL code' to anchor explanations to actual behaviour."
    assert "remaining_concerns" in system_content, \
        "System prompt must direct uncertain failures to remaining_concerns."
    assert "provably cause it" in system_content or "provably" in system_content, \
        "System prompt must require provable causation before claiming exceptions/failures."

    # R2: must prohibit adding new behaviour (exceptions, validation, etc.)
    assert "new behaviour" in system_content or "new behavior" in system_content, \
        "System prompt must prohibit adding new behaviour beyond fixing bugs."
    assert "raising exceptions" in system_content, \
        "System prompt must explicitly name 'raising exceptions' as a prohibited addition."
    assert "Preserve the original" in system_content, \
        "System prompt must require preserving original behaviour for unchanged inputs."

    # R3: must require each distinct bug to be its own issue entry.
    assert "each distinct bug" in system_content or "One issue per bug" in system_content, \
        "System prompt must require one issue entry per distinct bug."
    assert "own line" in system_content, \
        "System prompt must require each issue to have its own line number."

    # R4: must require specific line numbers, not whole-function ranges.
    assert "tight line range" in system_content or "specific line" in system_content, \
        "System prompt must require specific or tight line numbers."
    assert "not the whole function" in system_content, \
        "System prompt must prohibit whole-function line ranges."


@pytest.mark.asyncio
async def test_prompt_behavioural_rules_reach_model():
    """Mocked end-to-end: confirm the system message sent to the model
    contains all four behavioural rules (not just in _build_initial_messages)."""
    from app.services.debugging_service import DebuggingService

    captured_messages = []

    async def mock_generate(messages, **kwargs):
        captured_messages.extend(messages)
        return make_valid_reply()

    service = DebuggingService.__new__(DebuggingService)
    from unittest.mock import MagicMock
    service.client = MagicMock()
    service.client.generate_chat_completion = mock_generate
    service.client.model = "qwen/qwen-2.5-coder-32b-instruct"

    db = TestingSessionLocal()
    try:
        await service.analyze_code(
            __import__("app.schemas.debug", fromlist=["DebugRequest"]).DebugRequest(
                code="def f():\n    return 1\n",
                language="python",
            ),
            db,
        )
    finally:
        db.close()

    assert captured_messages, "No messages were captured"
    system_msg = next((m for m in captured_messages if m["role"] == "system"), None)
    assert system_msg is not None, "No system message was sent to the model"
    content = system_msg["content"]

    # All four rules must be present in what the model actually sees
    assert "ORIGINAL code" in content
    assert "provably" in content
    assert "new behaviour" in content or "new behavior" in content
    assert "One issue per bug" in content or "each distinct bug" in content
    assert "tight line range" in content or "specific line" in content
    assert "not the whole function" in content
