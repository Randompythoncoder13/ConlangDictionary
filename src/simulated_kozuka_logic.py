import random

"""
This logic was mimicked from the online site https://kozuka.kmwc.org/.  This code was written simply by looking at the 
"How to use" page (https://kozuka.kmwc.org/help.html) and making python code that does the same.  The Kozuka program is
an open-source program that can be found here: https://github.com/auctumnus/kotobazukashii.
"""


def find_matching_bracket(s, start_index):
    """
    Finds the index of the matching closing bracket for the one at start_index.
    Handles nested brackets.
    """
    open_char = s[start_index]
    close_char = {'(': ')', '[': ']', '{': '}'}.get(open_char)
    if close_char is None:
        return -1  # Not an opening bracket

    depth = 1
    for i in range(start_index + 1, len(s)):
        if s[i] == open_char:
            depth += 1
        elif s[i] == close_char:
            depth -= 1

        if depth == 0:
            return i

    return -1  # No matching bracket found


def split_by_top_level_slash(s):
    """
    Splits a string by '/' but ignores '/' inside nested brackets.
    Example: 'a/b/[c/d]/(e/f)' -> ['a', 'b', '[c/d]', '(e/f)']
    """
    parts = []
    depth = 0
    current_part_start = 0

    for i, char in enumerate(s):
        if char in '([':
            depth += 1
        elif char in ')]':
            if depth > 0:
                depth -= 1
        elif char == '/' and depth == 0:
            parts.append(s[current_part_start:i])
            current_part_start = i + 1

    parts.append(s[current_part_start:])
    return parts


def parse_weight(option_string):
    """
    Parses a pattern string like 'a*b*2' into ('a*b', 2).
    If no valid weight is found, returns (original_string, 1).
    """
    last_asterisk = option_string.rfind('*')
    if last_asterisk != -1:
        try:
            # Try to convert the part after the asterisk to an int
            weight_str = option_string[last_asterisk + 1:]
            if not weight_str:  # Handle trailing asterisk like 'a*'
                return option_string, 1
            weight = int(weight_str)
            # If successful, the base pattern is everything before it
            base_pattern = option_string[:last_asterisk]
            return base_pattern, weight
        except ValueError:
            # It wasn't a number, so it's a literal part of the pattern
            pass

    # No valid weight found
    return option_string, 1


def process_sequence(pattern, definitions):
    """
    Processes a pattern as a sequence of components (literals, {}, [], ()).
    This function handles the *sequence* part, not the *choice* part.
    """
    result = ""
    i = 0
    while i < len(pattern):
        char = pattern[i]

        if char == '{':
            j = find_matching_bracket(pattern, i)
            if j == -1:
                # Handle error: unclosed bracket
                result += char  # Treat as literal
                i += 1
                continue

            ref_name = pattern[i + 1:j]
            if ref_name in definitions:
                # Recurse: evaluate the definition
                result += evaluate_pattern(definitions[ref_name], definitions)
            # else: definition not found, treat as empty
            i = j + 1

        elif char == '[':  # Mandatory group
            j = find_matching_bracket(pattern, i)
            if j == -1:
                result += char
                i += 1
                continue

            sub_pattern = pattern[i + 1:j]
            # Recurse: evaluate the sub-pattern
            result += evaluate_pattern(sub_pattern, definitions)
            i = j + 1

        elif char == '(':  # Optional group
            j = find_matching_bracket(pattern, i)
            if j == -1:
                result += char
                i += 1
                continue

            # 50% chance to process, 50% chance to skip
            if random.random() < 0.5:
                sub_pattern = pattern[i + 1:j]
                # Recurse: evaluate the sub-pattern
                result += evaluate_pattern(sub_pattern, definitions)
            i = j + 1

        else:  # Literal
            result += char
            i += 1

    return result


def evaluate_pattern(pattern, definitions):
    """
    Evaluates a pattern string.
    This function handles the *choice* (a/b/c) and *weight* (a*2) logic.
    It then delegates to process_sequence to handle the chosen pattern.
    """
    # 1. Handle choices (a/b/c)
    options = split_by_top_level_slash(pattern)

    # 2. Handle weights (a*2/b)
    weighted_list = []
    if not options:
        return ""

    for option in options:
        base_pattern, weight = parse_weight(option)
        weighted_list.extend([base_pattern] * weight)

    # 3. Choose one
    chosen_pattern = random.choice(weighted_list)

    # 4. Process the chosen pattern as a sequence
    return process_sequence(chosen_pattern, definitions)


def generate_words(main_pattern, definitions_list, count=1):
    """
    Main function to generate words based on the rules.

    Args:
        main_pattern (str): The top-level pattern string, e.g., "{C}{V}".
        definitions_list (list): A list of dicts, e.g., [{"C": "p/t/k"}, {"V": "a/i"}].
        count (int): The number of words to generate.

    Returns:
        list: A list of generated word strings.
    """

    print("called")

    # Convert list of dicts to a single dict for easier lookup
    definitions = {}
    for d in definitions_list:
        definitions.update(d)

    # Split pattern into base and filters
    if '^' in main_pattern:
        parts = main_pattern.split('^')
        base_pattern = parts[0]
        filters = parts[1:]
    else:
        base_pattern = main_pattern
        filters = []

    generated_words = []
    attempts = 0  # Safety break to avoid infinite loops

    while len(generated_words) < count and attempts < (count * 10 + 100):
        attempts += 1
        word = evaluate_pattern(base_pattern, definitions)

        # Check against filters
        is_valid = True
        if filters:
            for f in filters:
                if f in word:
                    is_valid = False
                    break

        if is_valid and word not in generated_words:
            generated_words.append(word)

    if attempts >= (count * 1000 + 100):
        print(f"Warning: Hit max attempts ({attempts}). Could only generate {len(generated_words)} words.")
        print("This may be due to overly restrictive filters.")

    print("completed")
    return generated_words


# --- Example Usage ---
if __name__ == "__main__":
    # 1. Simple example
    print("--- Simple Example (tets.txt) ---")
    simple_defs = [{"C": "p/t/k"}, {"V": "a/i"}]
    simple_pattern = "{C}{V}"
    print(f"Pattern: {simple_pattern}")
    print(f"Definitions: {simple_defs}")
    print("Generated words:")
    print(generate_words(simple_pattern, simple_defs, count=10))
    print("-" * 20)

    # 2. Complex nested example
    print("--- Complex Nested Example ---")
    complex_defs = [{"C": "p/t/k/b/c/d/f/g/h/j/k"}, {"V": "a/e/i/o/u"}]
    complex_pattern = "(({C})({V})){C}{V}({V}){C}(({C}){V}({C}))"
    print(f"Pattern: {complex_pattern}")
    print(f"Definitions: {complex_defs}")
    print("Generated words:")
    print(generate_words(complex_pattern, complex_defs, count=10))
    print("-" * 20)

    # 3. Example with filters
    print("--- Filter Example ---")
    filter_defs = [{"C": "p/t/k"}, {"V": "a/i"}]
    # This pattern will generate "pa", "pi", "ta", "ti", "ka", "ki"
    # The filter ^pa will reject any words containing "pa".
    filter_pattern = "{C}{V}^pa^ki"
    print(f"Pattern: {filter_pattern}")
    print(f"Definitions: {filter_defs}")
    print("Generated words (will not contain 'pa' or 'ki'):")
    print(generate_words(filter_pattern, filter_defs, count=10))
    print("-" * 20)
