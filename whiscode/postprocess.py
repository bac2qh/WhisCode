import re

SYMBOL_MAP = {
    "slash": "/",
    "forward slash": "/",
    "backslash": "\\",
    "back slash": "\\",
    "dash": "-",
    "hyphen": "-",
    "underscore": "_",
    "dot": ".",
    "period": ".",
    "colon": ":",
    "semicolon": ";",
    "comma": ",",
    "equals": "=",
    "equal sign": "=",
    "plus": "+",
    "minus": "-",
    "open paren": "(",
    "close paren": ")",
    "open bracket": "[",
    "close bracket": "]",
    "open brace": "{",
    "close brace": "}",
    "open angle": "<",
    "close angle": ">",
    "at sign": "@",
    "hash": "#",
    "dollar sign": "$",
    "percent": "%",
    "caret": "^",
    "ampersand": "&",
    "star": "*",
    "asterisk": "*",
    "pipe": "|",
    "tilde": "~",
    "backtick": "`",
    "bang": "!",
    "exclamation": "!",
    "question mark": "?",
    "single quote": "'",
    "double quote": '"',
    "space": " ",
}

LITERAL_MAP = {
    "new line": "\n",
    "newline": "\n",
    "tab": "\t",
}


_CASE_LOOKAHEAD = r"(?=\s+(?:camel|snake|kebab|pascal|upper)\s+case|\s+spell\s|\s*$|\s*[^a-zA-Z0-9\s])"
_CASE_BODY = r"((?:[a-zA-Z]+(?:\s+(?=[a-zA-Z]))?)+ [a-zA-Z]+)"


def _apply_casing(text: str) -> str:
    def camel_case(match: re.Match) -> str:
        words = match.group(1).strip().split()
        if not words:
            return ""
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])

    def snake_case(match: re.Match) -> str:
        words = match.group(1).strip().split()
        return "_".join(w.lower() for w in words)

    def kebab_case(match: re.Match) -> str:
        words = match.group(1).strip().split()
        return "-".join(w.lower() for w in words)

    def pascal_case(match: re.Match) -> str:
        words = match.group(1).strip().split()
        return "".join(w.capitalize() for w in words)

    def upper_case(match: re.Match) -> str:
        words = match.group(1).strip().split()
        return "_".join(w.upper() for w in words)

    for prefix, fn in [("camel", camel_case), ("snake", snake_case), ("kebab", kebab_case), ("pascal", pascal_case), ("upper", upper_case)]:
        text = re.sub(rf"(?i){prefix} case\s+{_CASE_BODY}{_CASE_LOOKAHEAD}", fn, text)
    return text


def _apply_spelling(text: str) -> str:
    def spell_replace(match: re.Match) -> str:
        letters = match.group(1).strip().split()
        return "".join(letters)

    return re.sub(r"(?i)spell\s+((?:[a-z]\s+)*[a-z])(?=\s|$|[.,;:!?])", spell_replace, text)


def _apply_symbols(text: str) -> str:
    sorted_keys = sorted(SYMBOL_MAP.keys(), key=len, reverse=True)
    pattern = "|".join(re.escape(k) for k in sorted_keys)
    return re.sub(
        rf"(?i)\b({pattern})\b",
        lambda m: SYMBOL_MAP[m.group(1).lower()],
        text,
    )


def _apply_literals(text: str) -> str:
    sorted_keys = sorted(LITERAL_MAP.keys(), key=len, reverse=True)
    pattern = "|".join(re.escape(k) for k in sorted_keys)
    return re.sub(
        rf"(?i)\b({pattern})\b",
        lambda m: LITERAL_MAP[m.group(1).lower()],
        text,
    )


OPENING_SYMBOLS = set("(/[{<")
CLOSING_SYMBOLS = set(")/]}>.,;:!?")
NO_SPACE_AFTER = set("/\\@#~`")
NO_SPACE_BEFORE = set("/\\")
KEEP_SPACES = set("=+-*|&^%")


def _collapse_spaces(text: str) -> str:
    result = list(text)
    i = 0
    while i < len(result):
        ch = result[i]
        if ch in KEEP_SPACES:
            i += 1
            continue
        if ch in OPENING_SYMBOLS or ch in NO_SPACE_AFTER:
            while i > 0 and result[i - 1] == " ":
                result.pop(i - 1)
                i -= 1
            while i + 1 < len(result) and result[i + 1] == " ":
                result.pop(i + 1)
        if ch in CLOSING_SYMBOLS or ch in NO_SPACE_BEFORE:
            while i > 0 and result[i - 1] == " ":
                result.pop(i - 1)
                i -= 1
        i += 1
    return "".join(result)


def strip_repetitions(text: str, min_repeats: int = 5, max_phrase_len: int = 10) -> str:
    """Collapse runs of min_repeats+ consecutive identical phrases to a single occurrence.

    Checks phrase lengths from 1 up to max_phrase_len words. Comparison is
    case-insensitive; the first occurrence's casing is preserved.
    """
    tokens = text.split()
    if not tokens:
        return text
    for n in range(1, max_phrase_len + 1):
        if len(tokens) < n * min_repeats:
            continue
        tokens_lower = [t.lower() for t in tokens]
        i = 0
        result = []
        while i < len(tokens):
            if i + n > len(tokens):
                result.extend(tokens[i:])
                break
            phrase_lower = tokens_lower[i:i+n]
            count = 1
            while i + (count + 1) * n <= len(tokens):
                if tokens_lower[i + count * n : i + (count + 1) * n] == phrase_lower:
                    count += 1
                else:
                    break
            if count >= min_repeats:
                result.extend(tokens[i:i+n])
                i += count * n
            else:
                result.append(tokens[i])
                i += 1
        tokens = result
    return " ".join(tokens)


def postprocess_for_refine(text: str, replacements: dict[str, str] | None = None) -> str:
    """Minimal postprocessing for use before LLM refinement.

    Only strips Whisper hallucination repetitions and applies user replacements.
    Skips code-oriented transforms (symbols, casing, spelling, space collapse).
    """
    text = strip_repetitions(text)
    if replacements:
        from whiscode.hotwords import apply_replacements
        text = apply_replacements(text, replacements)
    return text


def postprocess(text: str, replacements: dict[str, str] | None = None) -> str:
    text = strip_repetitions(text)
    if replacements:
        from whiscode.hotwords import apply_replacements
        text = apply_replacements(text, replacements)
    text = _apply_symbols(text)
    text = _apply_literals(text)
    text = _apply_casing(text)
    text = _apply_spelling(text)
    text = _collapse_spaces(text)
    return text
