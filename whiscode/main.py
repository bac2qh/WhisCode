import argparse
import os
import signal
import subprocess
import sys
import threading
from enum import Enum
from pathlib import Path

from pynput import keyboard

from whiscode.hotwords import load_hotwords
from whiscode.injector import type_text
from whiscode.postprocess import postprocess
from whiscode.recorder import Recorder, SAMPLE_RATE
from whiscode.reminders import start_reminders
from whiscode.stats import Stats
from whiscode.transcriber import transcribe


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


def beep_start():
    subprocess.Popen(
        ["afplay", "-v", "0.5", "/System/Library/Sounds/Morse.aiff"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def beep_stop():
    subprocess.Popen(
        ["afplay", "-v", "0.5", "/System/Library/Sounds/Frog.aiff"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="WhisCode: Voice-to-keyboard for code dictation")
    parser.add_argument("--hotkey", default="shift_r", help="Toggle key for recording (default: shift_r)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-mlx", help="Whisper model to use")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--prompt", default=None, help="Additional context prompt to improve transcription accuracy")
    parser.add_argument("--hotwords-file", default=None, help="Path to hotwords config file (default: ~/.config/whiscode/hotwords.txt)")
    return parser.parse_args()


def main():
    args = parse_args()

    hotkey = getattr(keyboard.Key, args.hotkey, None)
    if hotkey is None:
        print(f"Error: Unknown hotkey '{args.hotkey}'. Use keys like shift_r, f10, ctrl, alt, etc.")
        sys.exit(1)

    model_path = args.model
    cache_dir = Path.home() / ".cache/huggingface/hub" / f"models--{args.model.replace('/', '--')}" / "snapshots/main"
    if cache_dir.exists():
        model_path = str(cache_dir)

    from pathlib import Path as P
    hotwords_path = P(args.hotwords_file) if args.hotwords_file else None
    hot_words, replacements = load_hotwords(hotwords_path) if hotwords_path else load_hotwords()
    if hot_words or replacements:
        print(f"Loaded {len(hot_words)} hot word(s) and {len(replacements)} replacement(s).")

    print(f"Loading model: {model_path} ...")
    from mlx_audio.stt.utils import load_model
    model = load_model(model_path)
    print(f"Model loaded. Press {args.hotkey} to start/stop recording.")

    stats = Stats()
    start_reminders(stats)

    state = State.IDLE
    state_lock = threading.Lock()
    recorder = Recorder()

    def on_press(key):
        nonlocal state
        if key != hotkey:
            return

        with state_lock:
            if state == State.TRANSCRIBING:
                return

            if state == State.IDLE:
                state = State.RECORDING
                recorder.start()
                beep_start()
                print("Recording...")

            elif state == State.RECORDING:
                state = State.TRANSCRIBING
                audio = recorder.stop()
                beep_stop()
                print("Transcribing...")

                audio_seconds = len(audio) / SAMPLE_RATE

                def process():
                    nonlocal state
                    try:
                        text = transcribe(model, audio, language=args.language, extra_prompt=args.prompt, hotwords=hot_words)
                        if text:
                            processed = postprocess(text, replacements=replacements)
                            word_count = len(processed.split())
                            stats.record(word_count, audio_seconds)
                            print(f"  > {processed}")
                            type_text(processed)
                        else:
                            print("  (no speech detected)")
                    except Exception as e:
                        print(f"  Error: {e}", file=sys.stderr)
                    finally:
                        with state_lock:
                            state = State.IDLE

                threading.Thread(target=process, daemon=True).start()

    shutdown_event = threading.Event()
    ctrl_c_count = 0

    def handle_signal(signum, frame):
        nonlocal ctrl_c_count
        ctrl_c_count += 1
        shutdown_event.set()
        if ctrl_c_count >= 2:
            os._exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    while listener.is_alive() and not shutdown_event.is_set():
        listener.join(timeout=0.5)

    listener.stop()

    with state_lock:
        if state == State.RECORDING:
            recorder.stop()

    print(f"\nSession stats: {stats.summary()}")
    print("Exiting.")


if __name__ == "__main__":
    main()
