import asyncio
from app.services.openrouter_client import OpenRouterClient
from app.services.debugging_service import DebuggingService, format_code_with_line_numbers

code = """def find_max(numbers):
    \"\"\"Return the largest number in the list.\"\"\"
    max_val = 0
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

print(find_max([3, 1, 4, 1, 5, 9]))   # expected 9
print(find_max([-3, -1, -4]))          # expected -1, returns 0 (bug)
"""

async def debug_one():
    client = OpenRouterClient()
    service = DebuggingService(client)
    numbered, total = format_code_with_line_numbers(code)
    messages = service._build_initial_messages(code, "python", numbered, total)
    raw = await client.generate_chat_completion(messages, temperature=0.0)
    print("=== RAW OUTPUT ===")
    print(raw)
    print("=== END RAW OUTPUT ===")

if __name__ == "__main__":
    asyncio.run(debug_one())
