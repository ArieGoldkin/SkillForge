# Collapsible Sections Demo

This markdown demonstrates the new collapsible functionality that will work in SkillForge artifacts.

## Basic Collapsible

<details>
<summary>Click to expand this section</summary>

This content is hidden by default and will only show when the user clicks the summary.

You can include **any markdown** inside, including:
- Lists
- Code blocks
- Tables

</details>

---

## Multiple Sections

<details>
<summary>Section 1: Introduction</summary>

This is the first collapsible section.

</details>

<details>
<summary>Section 2: Details</summary>

This is the second collapsible section.

</details>

<details>
<summary>Section 3: Conclusion</summary>

This is the third collapsible section.

</details>

---

## Code Inside Collapsible

<details>
<summary>Solution (click to reveal)</summary>

```python
def factorial(n):
    """Calculate factorial recursively."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Test it
print(factorial(5))  # Output: 120
```

The solution uses recursion to calculate the factorial.

</details>

---

## Exercise with Hints and Solution

### Exercise: Implement Binary Search

Write a function that performs binary search on a sorted array.

<details>
<summary>Hints (click to expand)</summary>

1. Start with two pointers: left and right
2. Calculate the middle index
3. Compare the middle element with the target
4. Adjust pointers based on comparison

</details>

<details>
<summary>Solution (click to expand)</summary>

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1  # Not found

# Test cases
arr = [1, 3, 5, 7, 9, 11, 13]
print(binary_search(arr, 7))   # Output: 3
print(binary_search(arr, 6))   # Output: -1
```

**Time Complexity**: O(log n)
**Space Complexity**: O(1)

</details>

---

## Visual Hierarchy Features

Notice how this document has:

1. **Section dividers** (• • •) between major sections
2. **Progressive heading spacing** - larger headings have more breathing room
3. **Clear visual breaks** making the document scannable
4. **Collapsible content** reducing cognitive load

### Subheading Example

This demonstrates the hierarchy between H2 and H3 headings.

#### Even Smaller Heading (H4)

The spacing gets progressively smaller as headings get less important.

##### Smallest Heading (H5)

Still readable but clearly subordinate to larger headings.

###### Micro Heading (H6)

The smallest heading level with muted color.

---

## Real-World Artifact Use Case

In a SkillForge artifact, the template includes:

- **Exercise hints**: Hidden by default, reveal when stuck
- **Exercise solutions**: Collapsed to prevent spoilers
- **Quiz answers**: Expandable after attempting the question
- **Agent findings**: Detailed analysis collapsed for scannability

This creates a **progressive disclosure** pattern where users see summaries first and can dive deeper as needed.

---

*This example demonstrates all the new features implemented for the artifact page UI improvements.*
