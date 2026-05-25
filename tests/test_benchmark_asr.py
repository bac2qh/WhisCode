from whiscode.benchmark_asr import parse_args


def test_benchmark_parse_args_accepts_mlx_vibevoice():
    args = parse_args([
        "--audio",
        "sample.wav",
        "--asr-backend",
        "mlx-vibevoice",
        "--mlx-vibevoice-model",
        "/tmp/VibeVoice-ASR-8bit",
        "--mlx-vibevoice-max-tokens",
        "2048",
        "--mlx-vibevoice-temperature",
        "0.2",
        "--mlx-vibevoice-prefill-step-size",
        "512",
    ])

    assert args.asr_backend == "mlx-vibevoice"
    assert args.mlx_vibevoice_model == "/tmp/VibeVoice-ASR-8bit"
    assert args.mlx_vibevoice_max_tokens == 2048
    assert args.mlx_vibevoice_temperature == 0.2
    assert args.mlx_vibevoice_prefill_step_size == 512
