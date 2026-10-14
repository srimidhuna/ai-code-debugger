import asyncio
import os
import sys
import json
import httpx

API_BASE = "http://localhost:8000/api"

EXAMPLES = [
    {
        "language": "python",
        "filename": "find_max.py",
        "code": """def find_max(numbers):
    \"\"\"Return the largest number in the list.\"\"\"
    max_val = 0
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

print(find_max([3, 1, 4, 1, 5, 9]))   # expected 9
print(find_max([-3, -1, -4]))          # expected -1, returns 0 (bug)
"""
    },
    {
        "language": "java",
        "filename": "StringReverser.java",
        "code": """public class StringReverser {
    public static String reverse(String str) {
        char[] chars = str.toCharArray();
        for (int i = 0; i < chars.length; i++) {   // bug: should be chars.length / 2
            char temp = chars[i];
            chars[i] = chars[chars.length - 1 - i];
            chars[chars.length - 1 - i] = temp;
        }
        return new String(chars);
    }

    public static void main(String[] args) {
        System.out.println(reverse("hello"));   // expected "olleh", returns "hello"
    }
}
"""
    },
    {
        "language": "c",
        "filename": "factorial.c",
        "code": """#include <stdio.h>

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
    },
    {
        "language": "cpp",
        "filename": "stack.cpp",
        "code": """#include <iostream>
#define MAX 5

class Stack {
    int items[MAX];
    int top;
public:
    Stack() : top(-1) {}

    void push(int val) {
        if (top >= MAX - 1) {
            std::cout << "Stack overflow\\n";
            return;
        }
        items[++top] = val;
    }

    int pop() {
        // bug: no empty-check before decrement
        return items[top--];
    }

    bool isEmpty() { return top == -1; }
};

int main() {
    Stack s;
    s.push(10);
    std::cout << s.pop() << "\\n";   // ok
    std::cout << s.pop() << "\\n";   // undefined behaviour: top becomes -2
}
"""
    },
    {
        "language": "javascript",
        "filename": "average.js",
        "code": """function average(nums) {
  let sum = 0;
  for (let i = 0; i < nums.length; i++) {
    sum += nums[i] / nums.length;  // bug: division should be outside the loop
  }
  return sum;
}

console.log(average([10, 20, 30]));   // expected 20
console.log(average([1, 2, 3, 4]));   // expected 2.5
"""
    }
]

async def test_all():
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Check health
        health = await client.get(f"{API_BASE}/health")
        print(f"Health response: {health.status_code} - {health.json()}")

        for ex in EXAMPLES:
            lang = ex["language"]
            filename = ex["filename"]
            print(f"\n=======================================================")
            print(f"Testing {lang.upper()} ({filename})...")
            print("=======================================================")
            
            try:
                resp = await client.post(
                    f"{API_BASE}/debug",
                    json={"language": lang, "code": ex["code"]}
                )
                print(f"Status Code: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"Session ID: {data.get('id')}")
                    print(f"Model Name: {data.get('model_name')}")
                    print(f"Summary: {data.get('summary')}")
                    print(f"Issues detected ({len(data.get('issues', []))}):")
                    for iss in data.get('issues', []):
                        print(f"  - [{iss.get('severity')}] Line {iss.get('line')}: {iss.get('title')} ({iss.get('category')})")
                        print(f"    Suggestion: {iss.get('suggestion')}")
                    print(f"Changes applied ({len(data.get('changes', []))}):")
                    for chg in data.get('changes', []):
                        print(f"  - {chg.get('description')} (Reason: {chg.get('reason')})")
                    print(f"Fixed code preview (first 5 lines):")
                    fixed_lines = data.get('fixed_code', '').splitlines()[:5]
                    for fl in fixed_lines:
                        print(f"    {fl}")
                else:
                    print(f"ERROR Response: {resp.text}")
            except Exception as e:
                print(f"Exception during request: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_all())
