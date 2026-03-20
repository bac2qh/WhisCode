import argparse
import subprocess
import sys
import threading
from enum import Enum
from pathlib import Path

from pynput import keyboard

from whiscode.injector import type_text
from whiscode.postprocess import postprocess
from whiscode.recorder import Recorder
from whiscode.transcriber import transcribe


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


def beep():
    subprocess.Popen(
        ["afplay", "/System/Library/Sounds/Tink.aiff"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="WhisCode: Voice-to-keyboard for code dictation")
    parser.add_argument("--hotkey", default="shift_r", help="Toggle key for recording (default: shift_r)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-mlx", help="Whisper model to use")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--prompt", default=None, help="Additional context prompt to improve transcription accuracy")
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

    print(f"Loading model: {model_path} ...")
    from mlx_audio.stt.utils import load_model
    model = load_model(model_path)
    print(f"Model loaded. Press {args.hotkey} to start/stop recording.")

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
                beep()
                print("Recording...")

            elif state == State.RECORDING:
                state = State.TRANSCRIBING
                audio = recorder.stop()
                beep()
                print("Transcribing...")

                def process():
                    nonlocal state
                    try:
                        text = transcribe(model, audio, language=args.language, extra_prompt=args.prompt)
                        if text:
                            processed = postprocess(text)
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

    with keyboard.Listener(on_press=on_press) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nExiting.")


if __name__ == "__main__":
    main()
