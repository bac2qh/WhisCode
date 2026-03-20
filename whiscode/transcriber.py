import numpy as np

CODE_PROMPT = (
    "Programming terms: function, const, let, var, async, await, return, import, export, "
    "class, interface, type, enum, struct, impl, def, self, None, True, False, "
    "npm, pnpm, yarn, pip, uv, cargo, git, docker, kubectl, "
    "React, Next.js, TypeScript, JavaScript, Python, Rust, Go, "
    "API, REST, GraphQL, JSON, YAML, HTML, CSS, SQL, HTTP, HTTPS, URL, CLI, "
    "Claude, Anthropic, OpenAI, GPT, LLM, MLX, Whisper, "
    "localhost, env, config, utils, index, main, test, spec"
)


def transcribe(model, audio: np.ndarray, language: str = "en") -> str:
    if len(audio) == 0:
        return ""
    result = model.generate(
        audio,
        language=language,
        initial_prompt=CODE_PROMPT,
        verbose=False,
    )
    return (result.text or "").strip()
