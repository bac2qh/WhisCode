import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AudioFileHandler(FileSystemEventHandler):
    def __init__(self, pending_files: list, lock: threading.Lock):
        self.pending_files = pending_files
        self.lock = lock

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in ('.ogg', '.wav', '.mp3', '.m4a', '.flac'):
            with self.lock:
                self.pending_files.append(str(path))


class FileWatcher:
    def __init__(self, input_dir: Path):
        self.input_dir = Path(input_dir)
        self.pending_files: list[str] = []
        self.lock = threading.Lock()
        self.observer: Observer | None = None

    def start(self):
        self.input_dir.mkdir(parents=True, exist_ok=True)

        handler = AudioFileHandler(self.pending_files, self.lock)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.input_dir), recursive=False)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def get_next_file(self) -> str | None:
        with self.lock:
            if not self.pending_files:
                return None
            return self.pending_files.pop(0)

    def scan_existing(self):
        """Add any existing audio files to pending queue (for startup)."""
        extensions = ('.ogg', '.wav', '.mp3', '.m4a', '.flac')
        existing = sorted(
            [f for f in self.input_dir.iterdir() if f.suffix.lower() in extensions],
            key=lambda p: p.stat().st_mtime
        )
        with self.lock:
            for f in existing:
                self.pending_files.append(str(f))
