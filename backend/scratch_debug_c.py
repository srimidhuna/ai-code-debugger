import asyncio
from app.services.openrouter_client import OpenRouterClient
from app.services.debugging_service import (
    DebuggingService,
    format_code_with_line_numbers,
    extract_edits_from_text,
    validate_and_apply_edits
)

code_c = """#include <stdio.h>

int factorial(int n) {
    int result = 0;          /* bug: should be 1 */
    for (int i = 2; i <= n; i++) {   /* bug: should start at 1 (or 2 with result=1) */
        result *= i;
    }
    return result;
}

int main() {
    printf("5! = %d\\n", factorial(5));   /* expected 120, returns 0 */
    printf("0! = %d\\n", factorial(0));   /* expected 1,   returns 0 */
    return 0;
}
"""

async def test_c():
    client = OpenRouterClient()
    service = DebuggingService(client)
    numbered, total = format_code_with_line_numbers(code_c)
    messages = service._build_initial_messages(code_c, "c", numbered, total)
    raw = await client.generate_chat_completion(messages, temperature=0.0)
    print("=== RAW C OUTPUT ===")
    print(raw)
    edits, remainder = extract_edits_from_text(raw)
    print("Edits extracted:", edits)
    fixed = validate_and_apply_edits(code_c, edits, total)
    print("=== FIXED CODE ===")
    print(repr(fixed))
    print("=== SAFETY CHECK ===")
    try:
        service._validate_fixed_code_safety(code_c, fixed, "c")
        print("Safety check passed!")
    except Exception as e:
        print("Safety check failed:", e)

if __name__ == "__main__":
    asyncio.run(test_c())
