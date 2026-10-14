import re

code = '''#include <stdio.h>

int factorial(int n) {
    int result = 1;
    for (int i = 1; i <= n; i++) {
        result *= i;
    }
    return result;
}

int main() {
    printf("5! = %d\\n", factorial(5));   /* expected 120, returns 0 */
    printf("0! = %d\\n", factorial(0));   /* expected 1,   returns 0 */
    return 0;
}
'''

abnormal_patterns = [
    (1, r'=\s{4,}(?:for|while|if|def|class|return|function)\b'),
    (2, r';\s{4,}(?:for|while|if|def|class|return|int|float|double|char|void)\b'),
    (3, r'\}\s{4,}(?:for|while|if|def|class|return|int|float|double|char|void)\b'),
    (4, r'[a-zA-Z0-9_\)\]\}\+\-\*\/]return\b'),
]

for idx, p in abnormal_patterns:
    m = re.search(p, code)
    if m:
        print(f"Pattern {idx} matched: {repr(m.group(0))}")
