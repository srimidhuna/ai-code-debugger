"""
Debugging service with patch-based fixes:

  PART 1 — JSON metadata block (no code inside):
    {
      "summary": "...",
      "issues": [...],
      "changes": [...],
      "remaining_concerns": [...]
    }

  PART 2 — Line-targeted edits in delimited blocks:
    <edit start="10" end="10">
    <replacement>
            count += 1
    </replacement>
    </edit>

Keeping unchanged code completely untouched on the backend by applying validated
edits to the original source code guarantees that line breaks, blank lines,
and untouched functions are preserved byte for byte.
"""

import ast
import json
import logging
import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.ai_logging import log_raw_ai_response, log_ai_parse_error
from app.core.exceptions import (
    AIValidationError,
    SourceTooLargeError,
    SourceTooManyLinesError,
)
from app.models.session import SessionModel
from app.schemas.debug import AIAnalysisResult, DebugRequest
from app.services.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

MAX_BYTES = 102400
MAX_LINES = 3000
MAX_EDITS_PER_REQUEST = 30

# Delimiter tags for edits
EDIT_BLOCK_RE = re.compile(
    r'<edit\s+start="(\d+)"\s+end="(\d+)">\s*<replacement>(.*?)</replacement>\s*</edit>',
    re.DOTALL,
)


class CodeEdit(BaseModel):
    start_line: int = Field(..., description="1-based starting line number")
    end_line: int = Field(..., description="1-based ending line number (inclusive)")
    replacement_text: str = Field(..., description="Replacement text for lines [start_line, end_line]")


# ---------------------------------------------------------------------------
# Source validation helpers
# ---------------------------------------------------------------------------

def validate_source_limits(code: str) -> None:
    """Validate source code size and line limits in UTF-8 bytes."""
    encoded = code.encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise SourceTooLargeError()
    lines = code.splitlines()
    if len(lines) > MAX_LINES:
        raise SourceTooManyLinesError()


def format_code_with_line_numbers(code: str) -> Tuple[str, int]:
    """Format code with 1-based line numbers for AI context and return total line count."""
    lines = code.splitlines()
    total_lines = len(lines)
    formatted = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    return "\n".join(formatted), total_lines


# ---------------------------------------------------------------------------
# Tolerant JSON extraction
# ---------------------------------------------------------------------------

def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (common model output error)."""
    return re.sub(r",\s*(?=[}\]])", "", text)


def _repair_unquoted_keys(text: str) -> str:
    """Quote bare identifier keys wherever they appear in a JSON-like object."""
    return re.sub(
        r'(?<!")\b([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)(?!")',
        r'"\1"\2',
        text,
    )


def extract_json_from_text(text: str) -> dict:
    """Tolerantly extract and parse the first JSON object from raw LLM output.

    Handles:
    - Markdown code fences (```json ... ```) and plain (``` ... ```)
    - Trailing commas before } or ]
    - Unquoted identifier keys
    - Unescaped inner quotes or missing delimiters via json_repair
    """
    clean = text.strip()

    # Strip markdown code fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
    if fence:
        clean = fence.group(1).strip()

    # Extract first {...} block if there's surrounding prose
    brace_match = re.search(r"\{[\s\S]*\}", clean)
    if brace_match:
        clean = brace_match.group(0)

    # Attempt 1: raw parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Attempt 2: strip trailing commas
    repaired = _strip_trailing_commas(clean)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Attempt 3: repair unquoted keys then strip trailing commas
    repaired2 = _strip_trailing_commas(_repair_unquoted_keys(clean))
    try:
        return json.loads(repaired2)
    except json.JSONDecodeError:
        pass

    # Attempt 4: stateful json-repair for unescaped quotes, missing commas, or syntax glitches
    try:
        import json_repair
        decoded = json_repair.loads(clean)
        if isinstance(decoded, dict):
            return decoded
    except Exception:
        pass

    # Attempt 5: json-repair on remainder text directly
    try:
        import json_repair
        decoded = json_repair.loads(text)
        if isinstance(decoded, dict):
            return decoded
    except Exception:
        pass

    # If all attempts fail, raise AIValidationError
    try:
        json.loads(clean)
    except json.JSONDecodeError as exc:
        raise AIValidationError(f"Invalid JSON format in AI response: {exc}") from exc
    raise AIValidationError("Unable to extract valid JSON metadata from AI response.")


# ---------------------------------------------------------------------------
# Patch parsing, validation, and application
# ---------------------------------------------------------------------------

def extract_edits_from_text(text: str) -> Tuple[List[CodeEdit], str]:
    """Extract <edit start="..." end="..."> <replacement>...</replacement> </edit> blocks.
    Returns (list_of_CodeEdits, text_without_edit_blocks).
    """
    edits: List[CodeEdit] = []
    
    # Normalize CRLF and CR to LF across the text
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    for match in EDIT_BLOCK_RE.finditer(normalized):
        start_line = int(match.group(1))
        end_line = int(match.group(2))
        raw_replacement = match.group(3)
        
        # Remove at most one leading and at most one trailing newline inside <replacement>
        if raw_replacement.startswith("\n"):
            raw_replacement = raw_replacement[1:]
        if raw_replacement.endswith("\n"):
            raw_replacement = raw_replacement[:-1]

        edits.append(CodeEdit(
            start_line=start_line,
            end_line=end_line,
            replacement_text=raw_replacement,
        ))

    remainder = EDIT_BLOCK_RE.sub("", normalized)
    return edits, remainder


def validate_and_apply_edits(
    original_code: str,
    edits: List[CodeEdit],
    total_lines: int,
) -> str:
    """Validate and apply line-targeted edits to the original source code.

    Validation rules:
    - Sensible max number of edits (<= 30).
    - Ranges inside the file:
        - For replacement / deletion: 1 <= start_line <= end_line <= total_lines.
        - For insertion before start_line: end_line == start_line - 1, 1 <= start_line <= total_lines + 1.
    - No overlapping or out-of-order edits.
    - Replacement text lines not wildly longer than what they replace (e.g. max 100 extra lines per edit).

    Application guarantees:
    - Copies untouched lines byte for byte.
    - Preserves original newline style (CRLF vs LF).
    - Preserves trailing newline status of the original code.
    """
    if len(edits) > MAX_EDITS_PER_REQUEST:
        raise AIValidationError(
            f"Too many edits proposed ({len(edits)} > {MAX_EDITS_PER_REQUEST})."
        )

    # Detect original newline style
    is_crlf = "\r\n" in original_code
    has_trailing_newline = original_code.endswith("\r\n") or original_code.endswith("\n")

    # Split original code into lines (keeping clean LF for processing)
    norm_orig = original_code.replace("\r\n", "\n").replace("\r", "\n")
    orig_lines = norm_orig.splitlines()

    # Sort edits by start_line ascending
    sorted_edits = sorted(edits, key=lambda e: (e.start_line, e.end_line))

    # Validate boundaries and overlap
    prev_end = 0
    for edit in sorted_edits:
        is_insertion = (edit.end_line == edit.start_line - 1)
        
        if is_insertion:
            if edit.start_line < 1 or edit.start_line > total_lines + 1:
                raise AIValidationError(
                    f"Invalid insertion target line {edit.start_line} (file has {total_lines} lines)."
                )
            if edit.start_line <= prev_end:
                raise AIValidationError(
                    f"Overlapping or out-of-order edit at line {edit.start_line}."
                )
        else:
            if edit.start_line < 1 or edit.end_line > total_lines or edit.start_line > edit.end_line:
                raise AIValidationError(
                    f"Invalid edit range {edit.start_line}–{edit.end_line} (file has {total_lines} lines)."
                )
            if edit.start_line <= prev_end:
                raise AIValidationError(
                    f"Overlapping or out-of-order edit range {edit.start_line}–{edit.end_line}."
                )
            prev_end = edit.end_line

        # Line inflation sanity check: replacement lines not wildly longer
        replaced_count = 0 if is_insertion else (edit.end_line - edit.start_line + 1)
        repl_line_count = len(edit.replacement_text.splitlines()) if edit.replacement_text else 0
        if repl_line_count > replaced_count + 100:
            raise AIValidationError(
                f"Proposed replacement for lines {edit.start_line}–{edit.end_line} is unreasonably large "
                f"({repl_line_count} lines)."
            )

    # Apply edits cleanly
    new_lines: List[str] = []
    current_line = 1  # 1-based index in orig_lines

    for edit in sorted_edits:
        is_insertion = (edit.end_line == edit.start_line - 1)
        
        if is_insertion:
            # Copy untouched lines up to insertion point
            while current_line < edit.start_line:
                new_lines.append(orig_lines[current_line - 1])
                current_line += 1
            # Insert new lines if any
            if edit.replacement_text:
                new_lines.extend(edit.replacement_text.splitlines())
        else:
            # Copy untouched lines up to start_line
            while current_line < edit.start_line:
                new_lines.append(orig_lines[current_line - 1])
                current_line += 1
            # Substitute replacement text if not deletion
            if edit.replacement_text:
                new_lines.extend(edit.replacement_text.splitlines())
            # Skip replaced lines in original
            current_line = edit.end_line + 1

    # Copy any remaining untouched lines
    while current_line <= len(orig_lines):
        new_lines.append(orig_lines[current_line - 1])
        current_line += 1

    # Reassemble with original line endings
    newline_sep = "\r\n" if is_crlf else "\n"
    result = newline_sep.join(new_lines)
    if has_trailing_newline and (not result.endswith(newline_sep)):
        result += newline_sep

    return result


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

class DebuggingService:
    def __init__(self, client: Optional[OpenRouterClient] = None):
        self.client = client or OpenRouterClient()

    def _build_initial_messages(self, code: str, language: str, numbered_code: str, total_lines: int) -> list:
        system_prompt = (
            "You are an expert AI code debugger. Analyze the provided source code for "
            "syntax errors, logical errors, runtime errors, and code quality issues.\n\n"
            "Respond with EXACTLY TWO parts:\n\n"
            "PART 1: A raw JSON object with this exact schema:\n"
            "{\n"
            '  "summary": "High-level summary of findings",\n'
            '  "issues": [\n'
            "    {\n"
            '      "title": "Short issue title",\n'
            '      "severity": "Critical" | "High" | "Medium" | "Low",\n'
            '      "category": "Syntax" | "Logic" | "Runtime" | "Code Quality",\n'
            '      "line": <integer 1-based start line or null>,\n'
            '      "line_end": <integer 1-based end line or null>,\n'
            '      "explanation": "Why the bug occurs in the ORIGINAL code",\n'
            '      "suggestion": "How to fix it"\n'
            "    }\n"
            "  ],\n"
            '  "changes": [\n'
            "    {\n"
            '      "description": "What changed",\n'
            '      "reason": "Why"\n'
            "    }\n"
            "  ],\n"
            '  "remaining_concerns": ["Any warnings or ambiguities"]\n'
            "}\n\n"
            "PART 2: Line-targeted code edits.\n"
            "Do NOT output the full file. Output ONLY targeted edits for lines that have bugs using this exact syntax:\n\n"
            '<edit start="START_LINE" end="END_LINE">\n'
            "<replacement>\n"
            "REPLACEMENT_CODE_HERE\n"
            "</replacement>\n"
            "</edit>\n\n"
            "EDIT CONVENTIONS:\n"
            "- START_LINE and END_LINE are 1-based line numbers from the numbered input.\n"
            "- To replace lines 10 through 12: <edit start=\"10\" end=\"12\"><replacement>...</replacement></edit>\n"
            "- To delete line 5: <edit start=\"5\" end=\"5\"><replacement></replacement></edit>\n"
            "- To insert new code BEFORE line 8: <edit start=\"8\" end=\"7\"><replacement>new_line</replacement></edit>\n"
            "- If the code is already completely correct, do not output any <edit> blocks.\n\n"
            "CRITICAL RULES:\n"
            f"1. Valid line numbers: The original source has {total_lines} lines. Only reference valid line numbers (1–{total_lines}). "
            "Never specify overlapping edit ranges. Use specific line numbers or tight line ranges, not the whole function.\n"
            "2. Preserve indentation & line breaks: Every line in <replacement> must have proper indentation and its own newline.\n"
            "3. Minimal fix: Do NOT add new behaviour (e.g. raising exceptions, input validation, "
            "logging, or extra checks) beyond directly fixing the reported bugs. Preserve the original "
            "program's behaviour for all inputs that were not causing the bug.\n"
            "4. Describe actual behaviour: Each issue's explanation must describe what the ORIGINAL code "
            "actually does at that line. Do NOT claim an exception is raised or a failure occurs unless "
            "the original code would provably cause it; if it is only a possibility, list it in "
            "remaining_concerns instead.\n"
            "5. One issue per bug: Report each distinct bug as its own separate issue entry with its own "
            "line number. Do not merge multiple bugs into one issue.\n"
            "6. Check every function in the file separately, including loops that never terminate "
            "(e.g. a while loop whose condition variable is never updated inside the loop body), "
            "and report each distinct bug as its own issue.\n"
            "7. Keep unaffected code untouched: Do NOT emit edits for functions or lines that do not have bugs."
        )

        user_prompt = (
            f"Programming Language: {language}\n\n"
            f"Source Code (with 1-based line numbers for reference only):\n"
            f"```\n{numbered_code}\n```\n\n"
            "Provide Part 1 (JSON metadata) and Part 2 (line-targeted <edit> blocks)."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_retry_messages(
        self,
        original_messages: list,
        first_response: str,
        parse_error: str,
    ) -> list:
        retry_messages = list(original_messages)
        retry_messages.append({"role": "assistant", "content": first_response})
        retry_messages.append({
            "role": "user",
            "content": (
                f"Your previous response had an issue: {parse_error}\n\n"
                "Please correct and resubmit. Requirements:\n"
                "1. PART 1 must be a valid JSON object with all keys double-quoted and no trailing commas.\n"
                "2. PART 2 must contain line-targeted <edit start=\"...\" end=\"...\"><replacement>...</replacement></edit> "
                "blocks. Do NOT output the full file.\n"
                "3. Ensure line numbers are within range and non-overlapping. Ensure replacement code is properly indented "
                "with each statement on its own line."
            ),
        })
        return retry_messages

    def _parse_and_apply_response(
        self,
        raw_output: str,
        original_code: str,
        total_lines: int,
        stage: str,
    ) -> Tuple[dict, str]:
        """Parse raw model output into metadata dict and build fixed_code from patch edits.
        Raises AIValidationError on any parsing or patch application error.
        """
        log_raw_ai_response(stage, raw_output)

        edits, remainder = extract_edits_from_text(raw_output)

        try:
            metadata = extract_json_from_text(remainder)
        except AIValidationError as exc:
            raise AIValidationError(f"[{stage}] {exc.message}") from exc

        # If there are no edits and no issues reported, code is unchanged
        if not edits:
            # Check if there was legacy full file block
            fixed_code = original_code
        else:
            try:
                fixed_code = validate_and_apply_edits(original_code, edits, total_lines)
            except AIValidationError as exc:
                raise AIValidationError(f"[{stage}] {exc.message}") from exc

        return metadata, fixed_code

    def _validate_fixed_code_safety(self, original_code: str, fixed_code: str, language: str = "") -> None:
        """Safety check: ensure the corrected code does not have collapsed lines,
        syntax failures, or abnormal whitespace runs relative to the original source.
        """
        orig_norm = original_code.replace("\r\n", "\n").replace("\r", "\n")
        orig_lines = [l for l in orig_norm.splitlines() if l.strip()]
        fixed_lines = [l for l in fixed_code.splitlines() if l.strip()]

        # 1. Line count sanity check:
        # A legitimate bug fix should not collapse multi-line code into far fewer lines.
        if len(orig_lines) >= 3 and len(fixed_lines) < max(2, int(len(orig_lines) * 0.6)):
            raise AIValidationError(
                f"Proposed fix failed safety validation: line count collapsed from "
                f"{len(orig_lines)} to {len(fixed_lines)} non-empty lines. Line breaks may have been lost."
            )

        # 2. Python-specific validation: confirm code compiles using ast.parse only (never execute it)
        lang_lower = language.lower() if language else ""
        if lang_lower in ("python", "py"):
            try:
                ast.parse(fixed_code)
            except SyntaxError as syn_err:
                raise AIValidationError(
                    f"Proposed fix failed safety validation: corrected Python code has syntax error: {syn_err.msg} "
                    f"at line {syn_err.lineno}."
                ) from syn_err

        # 3. General check: abnormal whitespace runs indicating stripped newlines
        abnormal_patterns = [
            r'=\s{4,}(?:for|while|if|def|class|return|function)\b',
            r';\s{4,}(?:for|while|if|def|class|return|int|float|double|char|void)\b',
            r'\}\s{4,}(?:for|while|if|def|class|return|int|float|double|char|void)\b',
            r'[a-zA-Z0-9_\)\]\}\+\-\*\/]return\b',
        ]
        for pattern in abnormal_patterns:
            if re.search(pattern, fixed_code):
                raise AIValidationError(
                    "Proposed fix failed safety validation: statements appear to be concatenated "
                    "without necessary line breaks."
                )

    def _sanitize_line_numbers(self, analysis: AIAnalysisResult, total_lines: int) -> AIAnalysisResult:
        """Clamp or nullify line references that are outside source bounds."""
        for issue in analysis.issues:
            if issue.line is not None:
                if issue.line < 1 or issue.line > total_lines:
                    issue.explanation += (
                        f" (Note: Reported line {issue.line} is out of source bounds 1–{total_lines})"
                    )
                    issue.line = None
                    issue.line_end = None
                elif issue.line_end is not None and (
                    issue.line_end < issue.line or issue.line_end > total_lines
                ):
                    issue.line_end = issue.line
        return analysis

    async def analyze_code(self, request: DebugRequest, db: Session) -> SessionModel:
        """Analyze source code, generate fixes, validate response, and persist session."""
        validate_source_limits(request.code)
        numbered_code, total_lines = format_code_with_line_numbers(request.code)

        messages = self._build_initial_messages(
            code=request.code,
            language=request.language,
            numbered_code=numbered_code,
            total_lines=total_lines,
        )

        # ── First attempt ─────────────────────────────────────────────────
        raw_output = await self.client.generate_chat_completion(
            messages, temperature=0.0, use_json_mode=False
        )

        parsed_result: Optional[AIAnalysisResult] = None
        error_detail: Optional[str] = None
        first_raw: str = raw_output

        try:
            metadata, fixed_code = self._parse_and_apply_response(
                raw_output, request.code, total_lines, "attempt-1"
            )
            self._validate_fixed_code_safety(request.code, fixed_code, request.language)
            metadata["fixed_code"] = fixed_code
            parsed_result = AIAnalysisResult.model_validate(metadata)
        except Exception as exc:
            error_detail = str(exc)
            log_ai_parse_error("attempt-1", error_detail, raw_output)

        # ── Bounded retry (exactly once) ──────────────────────────────────
        if parsed_result is None:
            retry_messages = self._build_retry_messages(messages, first_raw, error_detail or "unknown error")
            retry_output = await self.client.generate_chat_completion(
                retry_messages, temperature=0.0, use_json_mode=False
            )

            try:
                metadata, fixed_code = self._parse_and_apply_response(
                    retry_output, request.code, total_lines, "retry-1"
                )
                self._validate_fixed_code_safety(request.code, fixed_code, request.language)
                metadata["fixed_code"] = fixed_code
                parsed_result = AIAnalysisResult.model_validate(metadata)
            except Exception as exc:
                retry_error = str(exc)
                log_ai_parse_error("retry-1", retry_error, retry_output)
                raise AIValidationError(
                    f"AI response failed schema validation after bounded retry: {retry_error}"
                ) from exc

        # ── Sanitize line numbers ─────────────────────────────────────────
        parsed_result = self._sanitize_line_numbers(parsed_result, total_lines)

        # ── Persist session with Pending status ───────────────────────────
        session_record = SessionModel(
            language=request.language,
            original_code=request.code,
            fixed_code=parsed_result.fixed_code,
            summary=parsed_result.summary,
            issues=[issue.model_dump() for issue in parsed_result.issues],
            changes=[change.model_dump() for change in parsed_result.changes],
            remaining_concerns=parsed_result.remaining_concerns,
            decision="Pending",
            model_name=self.client.model,
        )

        try:
            db.add(session_record)
            db.commit()
            db.refresh(session_record)
            return session_record
        except Exception as exc:
            db.rollback()
            raise exc
