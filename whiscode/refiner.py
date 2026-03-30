import http.client
import json
import re
import sys


_SYSTEM_PROMPT = (
    "You are a transcription polisher. The user will provide raw speech-to-text output. "
    "Your job is to produce clean, professional written text: fix grammar, remove filler words "
    "(um, uh, like, you know, so, basically, actually, I mean), fix run-on sentences, and improve clarity. "
    "Preserve all meaning and specific details. Do not add new content or opinions. "
    "Tone: business-appropriate — friendly and approachable but professional. No slang, no overly formal language. "
    "Structure: if the speaker lists items, format them as a flat numbered or bulleted list. "
    "Output only the polished text — no preamble, no explanation, no quotation marks."
)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks that some models (e.g. Qwen3) produce."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def refine(text: str, model: str = "qwen3.5:4b", host: str = "localhost", port: int = 11434) -> str:
    """Pass text through a local Ollama model for prose refinement.

    Falls back to returning the original text on any error.
    """
    if not text.strip():
        return text

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 512,
        },
    }).encode()

    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=30)
        conn.request("POST", "/api/chat", body=payload, headers={"Content-Type": "application/json"})
        response = conn.getresponse()

        if response.status != 200:
            print(f"  Warning: Ollama returned HTTP {response.status}, using original text.", file=sys.stderr)
            return text

        body = response.read().decode()
        data = json.loads(body)
        refined = data["message"]["content"].strip()
        return _strip_think_tags(refined) or text

    except ConnectionRefusedError:
        print(f"  Warning: Ollama not running at {host}:{port}, using original text.", file=sys.stderr)
        return text
    except Exception as e:
        print(f"  Warning: Refinement failed ({e}), using original text.", file=sys.stderr)
        return text
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
