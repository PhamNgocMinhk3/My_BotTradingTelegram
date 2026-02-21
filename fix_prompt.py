"""Script to remove orphaned old prompt lines from gemini_analyzer.py"""
import os

filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gemini_analyzer.py')

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Before: {len(lines)} lines")

# Remove lines 1886-2929 (0-indexed: 1885-2928)
# Keep lines 0-1884 (lines 1-1885) and lines 2929+ (line 2930+)
new_lines = lines[:1885] + lines[2929:]

print(f"After: {len(new_lines)} lines")
print(f"Removed: {len(lines) - len(new_lines)} lines")

# Verify the transition is clean
print(f"\nTransition area:")
for i in range(1882, min(1890, len(new_lines))):
    print(f"  Line {i+1}: {repr(new_lines[i][:80])}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("\nDone! File saved.")
