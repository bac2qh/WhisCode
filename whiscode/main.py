import argparse
import subprocess
import sys
import threading
from enum import Enum

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
    parser.add_argument("--hotkey", default="f10", help="Toggle key for recording (default: f10)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo", help="Whisper model to use")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading model: {args.model} ...")
    from mlx_audio.stt.utils import load_model
    model = load_model(args.model)
    print(f"Model loaded. Press {args.hotkey.upper()} to start/stop recording.")

    state = State.IDLE
    state_lock = threading.Lock()
    recorder = Recorder()

    hotkey_attr = getattr(keyboard.Key, args.hotkey, None)
    if hotkey_attr is None:
        print(f"Error: Unknown hotkey '{args.hotkey}'. Use keys like f1-f20, ctrl, alt, etc.")
        sys.exit(1)

    def on_press(key):
        nonlocal state
        if key != hotkey_attr:
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
                        text = transcribe(model, audio, language=args.language)
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
