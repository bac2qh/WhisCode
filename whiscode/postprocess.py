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


def postprocess(text: str) -> str:
    text = _apply_symbols(text)
    text = _apply_literals(text)
    text = _apply_casing(text)
    text = _apply_spelling(text)
    text = _collapse_spaces(text)
    return text
