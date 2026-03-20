#!/usr/bin/env bash
set -euo pipefail

# WhisCode installer
# Downloads uv, syncs dependencies, and fetches the Whisper model via curl
# (bypasses Python SSL issues with pyenv)

MODEL_DIR="$HOME/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-mlx/snapshots/main"
HF_BASE="https://huggingface.co"

# Files from mlx-community/whisper-large-v3-mlx
MLX_REPO="mlx-community/whisper-large-v3-mlx"
MLX_FILES="config.json weights.npz"

# Tokenizer files from openai/whisper-large-v3
OPENAI_REPO="openai/whisper-large-v3"
TOKENIZER_FILES="added_tokens.json merges.txt normalizer.json preprocessor_config.json special_tokens_map.json tokenizer_config.json tokenizer.json vocab.json"

check_prerequisites() {
    if [[ "$(uname)" != "Darwin" ]]; then
        echo "Error: WhisCode requires macOS with Apple Silicon (MLX)."
        exit 1
    fi

    if [[ "$(uname -m)" != "arm64" ]]; then
        echo "Error: WhisCode requires Apple Silicon (M1/M2/M3/M4)."
        exit 1
    fi

    if ! command -v curl &>/dev/null; then
        echo "Error: curl is required but not found."
        exit 1
    fi
}

install_uv() {
    if command -v uv &>/dev/null; then
        echo "uv is already installed."
    else
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

sync_dependencies() {
    echo "Installing Python dependencies..."
    uv sync
}

download_file() {
    local repo="$1"
    local file="$2"
    local dest="$MODEL_DIR/$file"

    if [[ -f "$dest" && -s "$dest" ]]; then
        echo "  $file (already exists, skipping)"
        return
    fi

    echo "  $file ..."
    curl -L --fail --progress-bar \
        "$HF_BASE/$repo/resolve/main/$file" \
        -o "$dest"
}

download_model() {
    echo "Downloading model files to $MODEL_DIR"
    mkdir -p "$MODEL_DIR"

    echo "From $MLX_REPO:"
    for file in $MLX_FILES; do
        download_file "$MLX_REPO" "$file"
    done

    echo "From $OPENAI_REPO (tokenizer):"
    for file in $TOKENIZER_FILES; do
        download_file "$OPENAI_REPO" "$file"
    done
}

main() {
    echo "=== WhisCode Installer ==="
    echo ""

    check_prerequisites
    install_uv
    sync_dependencies
    download_model

    echo ""
    echo "=== Installation complete ==="
    echo "Run WhisCode with:"
    echo "  uv run whiscode"
    echo ""
    echo "Options:"
    echo "  uv run whiscode --hotkey shift_r"
    echo "  uv run whiscode --language en"
    echo "  uv run whiscode --prompt 'my project terms'"
}

main
