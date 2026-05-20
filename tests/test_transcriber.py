import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest

from whiscode.transcriber import transcribe


class FakeProgressBar:
    def __init__(self, *args, **kwargs):
        self.n = 0
        self.total = kwargs.get("total")
        self.format_dict = {"rate": None}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, n=1):
        self.n += n
        self.format_dict["rate"] = 123.4

    def close(self):
        pass


class FakeTqdmModule:
    def tqdm(self, *args, **kwargs):
        return FakeProgressBar(*args, **kwargs)


def install_fake_model_module(module_name):
    fake_module = types.ModuleType(module_name)
    fake_module.tqdm = FakeTqdmModule()
    sys.modules[module_name] = fake_module
    return fake_module


def test_transcribe_reports_tqdm_progress_and_restores_module():
    module_name = "fake_mlx_whisper_success"
    fake_module = install_fake_model_module(module_name)
    original_tqdm = fake_module.tqdm
    events = []

    class FakeModel:
        def generate(self, audio, **kwargs):
            with fake_module.tqdm.tqdm(total=10, unit="frames", disable=False) as pbar:
                pbar.update(4)
                pbar.update(6)
            return SimpleNamespace(text=" hello ")

    FakeModel.__module__ = module_name

    text = transcribe(
        FakeModel(),
        np.ones(4, dtype=np.float32),
        progress_callback=lambda **progress: events.append(progress),
    )

    assert text == "hello"
    assert fake_module.tqdm is original_tqdm
    assert {"current_frames": 0, "total_frames": 10, "rate": None} in events
    assert {"current_frames": 4, "total_frames": 10, "rate": 123.4} in events
    assert {"current_frames": 10, "total_frames": 10, "rate": 123.4} in events


def test_transcribe_restores_tqdm_module_after_failure():
    module_name = "fake_mlx_whisper_failure"
    fake_module = install_fake_model_module(module_name)
    original_tqdm = fake_module.tqdm

    class FakeModel:
        def generate(self, audio, **kwargs):
            with fake_module.tqdm.tqdm(total=10, unit="frames", disable=False) as pbar:
                pbar.update(2)
            raise RuntimeError("decode failed")

    FakeModel.__module__ = module_name

    with pytest.raises(RuntimeError, match="decode failed"):
        transcribe(
            FakeModel(),
            np.ones(4, dtype=np.float32),
            progress_callback=lambda **progress: None,
        )

    assert fake_module.tqdm is original_tqdm
