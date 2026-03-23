import re
from pathlib import Path

DEFAULT_PATH = Path.home() / ".config" / "whiscode" / "hotwords.txt"


def load_hotwords(path: Path = DEFAULT_PATH) -> tuple[list[str], dict[str, str]]:
    words: list[str] = []
    replacements: dict[str, str] = {}

    if not path.exists():
        return words, replacements

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "->" in line:
            parts = line.split("->", 1)
            wrong = parts[0].strip()
            right = parts[1].strip()
            if wrong and right:
                replacements[wrong] = right
        else:
            words.append(line)

    return words, replacements


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    if not replacements:
        return text
    for wrong, right in replacements.items():
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        text = pattern.sub(right, text)
    return text
