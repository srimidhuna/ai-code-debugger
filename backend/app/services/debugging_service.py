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


def _extract_tag_content(tag: str, text: str, default: str = "") -> str:
    """Extract content inside <tag>...</tag>, ignoring case and trimming whitespace."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return default


def extract_tagged_metadata_from_text(text: str) -> dict:
    """Tolerantly extract summary, issues, changes, and remaining_concerns from tagged blocks.

    Handles:
    - <summary>...</summary>
    - Multiple <issue>...</issue> blocks with <title>, <severity>, <category>, <line>, <line_end>, <explanation>, <suggestion>
    - Multiple <change>...</change> blocks with <description>, <reason>
    - <remaining_concerns>...</remaining_concerns> or <concern>...</concern> tags
    - Tolerates inner quotes, markdown, code snippets, whitespace, and missing optional tags.
    """
    clean = text.strip()

    # 1. Summary
    summary = _extract_tag_content("summary", clean, "")

    # 2. Issues
    issues = []
    issue_blocks = re.findall(r"<issue>(.*?)</issue>", clean, flags=re.IGNORECASE | re.DOTALL)
    for block in issue_blocks:
        title = _extract_tag_content("title", block, "")
        severity = _extract_tag_content("severity", block, "")
        category = _extract_tag_content("category", block, "")
        line_str = _extract_tag_content("line", block, "")
        line_end_str = _extract_tag_content("line_end", block, "")
        explanation = _extract_tag_content("explanation", block, "")
        suggestion = _extract_tag_content("suggestion", block, "")

        line_num = int(line_str) if (line_str and line_str.isdigit()) else None
        line_end_num = int(line_end_str) if (line_end_str and line_end_str.isdigit()) else line_num

        issues.append({
            "title": title,
            "severity": severity,
            "category": category,
            "line": line_num,
            "line_end": line_end_num,
            "explanation": explanation,
            "suggestion": suggestion,
        })

    # 3. Changes
    changes = []
    change_blocks = re.findall(r"<change>(.*?)</change>", clean, flags=re.IGNORECASE | re.DOTALL)
    for block in change_blocks:
        description = _extract_tag_content("description", block, "")
        reason = _extract_tag_content("reason", block, "")
        changes.append({
            "description": description,
            "reason": reason,
        })

    # 4. Remaining Concerns
    remaining_concerns = []
    concerns_container = _extract_tag_content("remaining_concerns", clean, "")
    if concerns_container:
        sub_concerns = re.findall(r"<concern>(.*?)</concern>", concerns_container, flags=re.IGNORECASE | re.DOTALL)
        if sub_concerns:
            remaining_concerns = [c.strip() for c in sub_concerns if c.strip()]
        else:
            lines = [l.strip().lstrip("-* ").strip() for l in concerns_container.splitlines() if l.strip()]
            remaining_concerns = [l for l in lines if l.lower() not in ("none", "n/a", "no remaining concerns", "[]")]
    else:
        direct_concerns = re.findall(r"<concern>(.*?)</concern>", clean, flags=re.IGNORECASE | re.DOTALL)
        if direct_concerns:
            remaining_concerns = [c.strip() for c in direct_concerns if c.strip()]

    # If any tagged blocks were present, return the parsed metadata dict
    if summary or issues or change_blocks or concerns_container:
        if not summary:
            summary = "Code analysis complete."
        return {
            "summary": summary,
            "issues": issues,
            "changes": changes,
            "remaining_concerns": remaining_concerns,
        }

    # Fall back to JSON extraction if no XML tags found
    return extract_json_from_text(text)


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
        raise AIValidationError(f"Invalid JSON/tag format in AI response: {exc}") from exc
    raise AIValidationError("Unable to extract valid metadata from AI response.")


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
    warnings: Optional[List[str]] = None,
) -> str:
    """Validate and apply line-targeted edits to the original source code.

    Validation rules:
    - Sensible max number of edits (<= 30).
    - Ranges inside the file:
        - For replacement / deletion: 1 <= start_line <= end_line <= total_lines.
        - For insertion before start_line: end_line == start_line - 1, 1 <= start_line <= total_lines + 1.
    - Overlapping edits are automatically merged (the wider edit's replacement wins).
    - When overlapping edits are merged, a warning is appended to warnings (if provided).
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

    # Sort edits by start_line ascending; ties broken widest-range-first so merge keeps wider edit
    sorted_edits = sorted(edits, key=lambda e: (e.start_line, -e.end_line))

    # -------------------------------------------------------------------------
    # Merge overlapping edits.
    # Models sometimes emit both a wide block-level edit and a narrower line-level
    # edit for the same region (e.g. when restructuring an if/else block they emit
    # one edit for lines 7-12 and a second edit for line 12).  Keep the wider edit.
    # -------------------------------------------------------------------------
    merged: List[CodeEdit] = []
    for edit in sorted_edits:
        if not merged:
            merged.append(edit)
            continue
        prev = merged[-1]
        prev_is_ins = (prev.end_line == prev.start_line - 1)
        curr_is_ins = (edit.end_line == edit.start_line - 1)
        if not prev_is_ins and not curr_is_ins and edit.start_line <= prev.end_line:
            # Overlap detected — merge into the wider range, prefer the text of the
            # edit that exactly covers the merged span, falling back to prev's text.
            new_start = min(prev.start_line, edit.start_line)
            new_end   = max(prev.end_line,   edit.end_line)
            if prev.start_line == new_start and prev.end_line == new_end:
                winner_text = prev.replacement_text
            elif edit.start_line == new_start and edit.end_line == new_end:
                winner_text = edit.replacement_text
            else:
                winner_text = prev.replacement_text  # prev is always the wider due to sort
            warn_msg = (
                f"Merged overlapping edits [{prev.start_line}-{prev.end_line}] and "
                f"[{edit.start_line}-{edit.end_line}] into [{new_start}-{new_end}]."
            )
            logger.warning(warn_msg)
            if warnings is not None:
                warnings.append(warn_msg)
            merged[-1] = CodeEdit(
                start_line=new_start,
                end_line=new_end,
                replacement_text=winner_text,
            )
        else:
            merged.append(edit)
    sorted_edits = merged

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
                rep_lines = edit.replacement_text.splitlines()
                # Relative-indent adjustment:
                # The model sometimes over-indents replacement lines relative to where
                # they will be placed in the file (e.g. uses 8 spaces for a 4-space
                # indent context).  Correct this by comparing the minimum indentation
                # of non-empty replacement lines against the original target line's indent.
                #
                #  min_rep > orig_level  → over-indented: shift all content lines LEFT
                #  min_rep == 0 & orig_level > 0 → under-indented: shift content RIGHT
                #  min_rep == orig_level → already correct, no adjustment
                orig_target_line = orig_lines[edit.start_line - 1]
                orig_level = len(orig_target_line) - len(orig_target_line.lstrip())
                has_content = any(l.strip() for l in rep_lines)
                if has_content:
                    min_rep_indent = min(
                        len(l) - len(l.lstrip()) for l in rep_lines if l.strip()
                    )
                    if min_rep_indent > orig_level:
                        # Over-indented — shift every content line left by the excess.
                        # Blank/whitespace-only lines are left as-is.
                        shift = min_rep_indent - orig_level
                        rep_lines = [
                            l[shift:] if l.strip() else l for l in rep_lines
                        ]
                    elif min_rep_indent == 0 and orig_level > 0:
                        # Under-indented — prepend orig indentation to content lines.
                        orig_indent = " " * orig_level
                        rep_lines = [
                            f"{orig_indent}{l}" if l.strip() else l for l in rep_lines
                        ]
                new_lines.extend(rep_lines)
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
            "Format your response using structured XML-style tags:\n\n"
            "<summary>\n"
            "High-level summary of findings\n"
            "</summary>\n\n"
            "For each detected issue, output an <issue> block:\n"
            "<issue>\n"
            "<title>Short issue title</title>\n"
            "<severity>Critical | High | Medium | Low</severity>\n"
            "<category>Syntax | Logic | Runtime | Code Quality</category>\n"
            "<line>1-based start line number</line>\n"
            "<line_end>1-based end line number</line_end>\n"
            "<explanation>Why the bug occurs in the ORIGINAL code</explanation>\n"
            "<suggestion>How to fix it</suggestion>\n"
            "</issue>\n\n"
            "For each change applied in your fix, output a <change> block:\n"
            "<change>\n"
            "<description>What changed</description>\n"
            "<reason>Why the change was necessary</reason>\n"
            "</change>\n\n"
            "<remaining_concerns>\n"
            "Any warnings, edge cases, or potential concerns (or leave empty if none)\n"
            "</remaining_concerns>\n\n"
            "LINE-TARGETED CODE EDITS:\n"
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
            "EXAMPLE:\n"
            "<summary>Fixed off-by-one index error in get_first.</summary>\n"
            "<issue>\n"
            "<title>Incorrect Index</title>\n"
            "<severity>High</severity>\n"
            "<category>Logic</category>\n"
            "<line>2</line>\n"
            "<line_end>2</line_end>\n"
            "<explanation>words[1] returns the second item; array indices start at 0.</explanation>\n"
            "<suggestion>Change index to 0.</suggestion>\n"
            "</issue>\n"
            "<change>\n"
            "<description>Changed words[1] to words[0]</description>\n"
            "<reason>To correctly access the first element</reason>\n"
            "</change>\n"
            "<remaining_concerns></remaining_concerns>\n"
            '<edit start="2" end="2">\n'
            "<replacement>\n"
            "    return words[0];\n"
            "</replacement>\n"
            "</edit>\n\n"
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
            "7. If an index looks wrong (e.g. words[1] for the first word), fix the index; don't add guards.\n"
            "8. Keep unaffected code untouched: Do NOT emit edits for functions or lines that do not have bugs."
        )

        user_prompt = (
            f"Programming Language: {language}\n\n"
            f"Source Code (with 1-based line numbers for reference only):\n"
            f"```\n{numbered_code}\n```\n\n"
            "Analyze the code and respond using the tagged blocks (<summary>, <issue>, <change>, <remaining_concerns>, and <edit> blocks)."
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
                "Please correct and resubmit using tagged blocks:\n"
                "1. Provide <summary>, <issue> (with <title>, <severity>, <category>, <line>, <line_end>, <explanation>, <suggestion>), "
                "<change>, and <remaining_concerns> tags.\n"
                "2. Provide line-targeted <edit start=\"...\" end=\"...\"><replacement>...</replacement></edit> "
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
            metadata = extract_tagged_metadata_from_text(remainder)
        except AIValidationError as exc:
            raise AIValidationError(f"[{stage}] {exc.message}") from exc

        # If there are no edits and no issues reported, code is unchanged
        if not edits:
            fixed_code = original_code
        else:
            try:
                # Any warnings from merging overlapping edits are recorded into remaining_concerns
                concerns_list = metadata.setdefault("remaining_concerns", [])
                fixed_code = validate_and_apply_edits(
                    original_code, edits, total_lines, warnings=concerns_list
                )
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

        # 3. General check: abnormal horizontal whitespace runs indicating stripped newlines
        abnormal_patterns = [
            r'=[ \t]{4,}(?:for|while|if|def|class|return|function)\b',
            r';[ \t]{4,}(?:for|while|if|def|class|return|int|float|double|char|void)\b',
            r'\}[ \t]{4,}(?:for|while|if|def|class|return|int|float|double|char|void)\b',
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
