#!/usr/bin/env bash
set -euo pipefail

# WhisCode full installer
# Installs everything from install.sh, plus Ollama + Qwen3.5 4B for --refine mode

REFINE_MODEL="qwen3.5:4b"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_base_install() {
    echo "=== Running base WhisCode install ==="
    bash "$SCRIPT_DIR/install.sh"
}

install_ollama() {
    if command -v ollama &>/dev/null; then
        echo "Ollama is already installed."
        return
    fi

    if ! command -v brew &>/dev/null; then
        echo "Error: Homebrew is required to install Ollama. Install it from https://brew.sh"
        exit 1
    fi

    echo "Installing Ollama..."
    brew install --cask ollama
}

start_ollama_server() {
    if curl -sf http://localhost:11434/ &>/dev/null; then
        return 0  # already running
    fi

    echo "Starting Ollama server..."
    # Run ollama serve in background, log to /tmp in case of errors
    ollama serve >/tmp/ollama-serve.log 2>&1 &
    OLLAMA_PID=$!

    # Wait up to 30 seconds for the server to become ready
    for i in $(seq 1 30); do
        if curl -sf http://localhost:11434/ &>/dev/null; then
            echo "Ollama server ready."
            return 0
        fi
        sleep 1
    done

    echo "Error: Ollama server did not start within 30 seconds."
    echo "Check /tmp/ollama-serve.log for details."
    kill "$OLLAMA_PID" 2>/dev/null || true
    exit 1
}

pull_refine_model() {
    echo "Pulling refinement model: $REFINE_MODEL (~3.4 GB) ..."
    start_ollama_server
    ollama pull "$REFINE_MODEL"
}

main() {
    echo "=== WhisCode Full Installer (with Ollama --refine support) ==="
    echo ""

    run_base_install

    echo ""
    echo "=== Installing Ollama for --refine mode ==="
    install_ollama
    pull_refine_model

    echo ""
    echo "=== Full installation complete ==="
    echo "Run WhisCode with:"
    echo "  uv run whiscode"
    echo ""
    echo "Options:"
    echo "  uv run whiscode --hotkey shift_r"
    echo "  uv run whiscode --language en"
    echo "  uv run whiscode --prompt 'my project terms'"
    echo "  uv run whiscode --refine                        # prose mode via local LLM"
    echo "  uv run whiscode --refine --refine-model qwen3:30b-a3b"
}

main
