import importlib
from typing import Any, Callable

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

ProgressCallback = Callable[..., None]


def transcribe(
    model,
    audio: np.ndarray,
    language: str = "en",
    extra_prompt: str | None = None,
    hotwords: list[str] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> str:
    if len(audio) == 0:
        return ""
    prompt = CODE_PROMPT
    if extra_prompt:
        prompt = f"{prompt} {extra_prompt}"
    if hotwords:
        prompt = f"{prompt} {', '.join(hotwords)}"
    lang = None if language == "auto" else language
    with _patch_model_tqdm(model, progress_callback):
        result = model.generate(
            audio,
            language=lang,
            initial_prompt=prompt,
            verbose=False,
        )
    return (result.text or "").strip()


class _TqdmProgressWrapper:
    def __init__(self, original_tqdm: Any, progress_callback: ProgressCallback, *args: Any, **kwargs: Any):
        self._bar = original_tqdm(*args, **kwargs)
        self._progress_callback = progress_callback
        self._emit_progress()

    def __enter__(self):
        self._bar.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._emit_progress()
        return self._bar.__exit__(exc_type, exc, tb)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bar, name)

    def update(self, n: int | float = 1):
        result = self._bar.update(n)
        self._emit_progress()
        return result

    def close(self) -> None:
        self._emit_progress()
        return self._bar.close()

    def _emit_progress(self) -> None:
        try:
            format_dict = getattr(self._bar, "format_dict", {}) or {}
            self._progress_callback(
                current_frames=int(getattr(self._bar, "n", 0) or 0),
                total_frames=_optional_int(getattr(self._bar, "total", None)),
                rate=_optional_float(format_dict.get("rate")),
            )
        except Exception:
            return


class _TqdmModuleProxy:
    def __init__(self, original_module: Any, progress_callback: ProgressCallback):
        self._original_module = original_module
        self._progress_callback = progress_callback

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original_module, name)

    def tqdm(self, *args: Any, **kwargs: Any) -> _TqdmProgressWrapper:
        return _TqdmProgressWrapper(self._original_module.tqdm, self._progress_callback, *args, **kwargs)


class _patch_model_tqdm:
    def __init__(self, model: Any, progress_callback: ProgressCallback | None):
        self._model = model
        self._progress_callback = progress_callback
        self._module = None
        self._original_tqdm_module = None

    def __enter__(self):
        if self._progress_callback is None:
            return None
        module_name = type(self._model).__module__
        try:
            module = importlib.import_module(module_name)
        except (ImportError, TypeError, ValueError):
            return None
        original_tqdm_module = getattr(module, "tqdm", None)
        if original_tqdm_module is None or not hasattr(original_tqdm_module, "tqdm"):
            return None
        self._module = module
        self._original_tqdm_module = original_tqdm_module
        module.tqdm = _TqdmModuleProxy(original_tqdm_module, self._progress_callback)
        return None

    def __exit__(self, exc_type, exc, tb):
        if self._module is not None:
            self._module.tqdm = self._original_tqdm_module
        return False


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None
