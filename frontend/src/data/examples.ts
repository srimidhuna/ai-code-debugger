import { SupportedLanguage } from '../types';

export interface ExampleProgram {
  language: SupportedLanguage;
  filename: string;
  description: string;
  code: string;
}

export const EXAMPLE_PROGRAMS: ExampleProgram[] = [
  {
    language: 'python',
    filename: 'find_max.py',
    description: 'find_max() initialises max_val to 0, so it returns 0 for all-negative lists instead of the true maximum.',
    code: `def find_max(numbers):
    """Return the largest number in the list."""
    max_val = 0
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

print(find_max([3, 1, 4, 1, 5, 9]))   # expected 9
print(find_max([-3, -1, -4]))          # expected -1, returns 0 (bug)
`,
  },
  {
    language: 'java',
    filename: 'StringReverser.java',
    description: 'The loop bound uses str.length() instead of str.length() / 2, so it reverses the string twice and returns the original value.',
    code: `public class StringReverser {
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
`,
  },
  {
    language: 'c',
    filename: 'factorial.c',
    description: 'factorial() uses int return type and int accumulator, which overflows for n >= 13. The loop bound is also off-by-one (starts at 2, so n=0 and n=1 return 0 instead of 1).',
    code: `#include <stdio.h>

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
`,
  },
  {
    language: 'cpp',
    filename: 'stack.cpp',
    description: 'pop() on an empty Stack does not check whether the stack is empty before decrementing top, causing undefined behaviour (top underflows to -1).',
    code: `#include <iostream>
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
`,
  },
  {
    language: 'javascript',
    filename: 'average.js',
    description: 'average() divides by nums.length inside the loop instead of after it, so it accumulates a running average rather than summing all values first.',
    code: `function average(nums) {
  let sum = 0;
  for (let i = 0; i < nums.length; i++) {
    sum += nums[i] / nums.length;  // bug: division should be outside the loop
  }
  return sum;
}

console.log(average([10, 20, 30]));   // expected 20 — coincidentally correct here
console.log(average([1, 2, 3, 4]));   // expected 2.5 — coincidentally correct here
// The bug is a code quality / logic issue: it works for simple cases but
// is semantically wrong and fragile with floating-point accumulation.
`,
  },
];
