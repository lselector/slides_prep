#!/usr/bin/env python3
"""Transcribe MP3 audio files to text."""

# Usage:
#   python transcribe_mp3_to_txt.py <audio.mp3>
#   python transcribe_mp3_to_txt.py -m small audio.mp3
#   python transcribe_mp3_to_txt.py -e mlx audio.mp3
#   python transcribe_mp3_to_txt.py -l fr audio.mp3
#   python transcribe_mp3_to_txt.py --help
#
# Description:
#   Transcribes an MP3 audio file to text.
#   Supports two engines:
#     - "mlx" (default): lightning-whisper-mlx
#       optimized for Apple Silicon
#     - "whisper": faster-whisper
#       on CPU with int8 compute type
#
# Models (both engines):
#   tiny (default), base, small, medium
#   MLX also supports: distil-medium.en,
#     distil-small.en, large, large-v2, etc.
#
# Language:
#   Use -l/--language to specify language.
#   Default is "en" (English).
#   Use ISO 639-1 codes, e.g.:
#     en (English), fr (French),
#     es (Spanish), de (German),
#     ru (Russian), ja (Japanese), etc.
#   If not specified, defaults to English.
#
# Output:
#   Saves transcript to a .txt file
#   with the same name as the audio file.
#
# Examples:
#   python transcribe_mp3_to_txt.py rec.mp3
#   python transcribe_mp3_to_txt.py -m small rec.mp3
#   python transcribe_mp3_to_txt.py -e mlx rec.mp3
#   python transcribe_mp3_to_txt.py -e mlx -m tiny rec.mp3
#   python transcribe_mp3_to_txt.py -l fr french.mp3
#   python transcribe_mp3_to_txt.py -e mlx -l fr a.mp3

import argparse
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

os.environ["MKL_THREADING_LAYER"] = "GNU"
os.environ[
    "MKL_SERVICE_FORCE_INTEL"
] = "1"

import warnings
warnings.filterwarnings(
    "ignore", message=".*MKL.*"
)

WHISPER_MODELS = [
    "tiny", "base", "small", "medium",
]

MLX_MODELS = [
    "tiny", "base", "small", "medium",
    "distil-small.en", "distil-medium.en",
    "large", "large-v2", "distil-large-v2",
    "large-v3", "distil-large-v3",
]


# --------------------------------------------------------------
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe an MP3 audio file "
            "to text."
        ),
        epilog=(
            "Examples:\n"
            "  python transcribe_mp3_to_txt.py"
            " rec.mp3\n"
            "  python transcribe_mp3_to_txt.py"
            " -m small rec.mp3\n"
            "  python transcribe_mp3_to_txt.py"
            " -e mlx rec.mp3\n"
        ),
        formatter_class=(
            argparse.RawDescriptionHelpFormatter
        ),
    )
    parser.add_argument(
        "audio_file",
        help="Path to the MP3 file",
    )
    parser.add_argument(
        "-m", "--model",
        default="tiny",
        help=(
            "Model size: tiny (default), "
            "base, small, medium. "
            "MLX also supports distil-* and "
            "large variants."
        ),
    )
    parser.add_argument(
        "-e", "--engine",
        default="mlx",
        choices=["whisper", "mlx"],
        help=(
            "Engine: mlx (lightning-whisper"
            "-mlx for Apple Silicon, "
            "default) or whisper "
            "(faster-whisper on CPU)."
        ),
    )
    parser.add_argument(
        "-l", "--language",
        default="en",
        help=(
            "Language code (ISO 639-1). "
            "Default: en (English). "
            "Examples: fr (French), "
            "es (Spanish), de (German), "
            "ru (Russian), ja (Japanese)."
        ),
    )
    return parser.parse_args()


# --------------------------------------------------------------
def validate_model(engine, model):
    """Validate model name for the engine."""
    if engine == "whisper":
        if model not in WHISPER_MODELS:
            valid = ", ".join(WHISPER_MODELS)
            raise ValueError(
                f"Invalid model '{model}' "
                f"for whisper engine. "
                f"Valid: {valid}"
            )
    elif engine == "mlx":
        if model not in MLX_MODELS:
            valid = ", ".join(MLX_MODELS)
            raise ValueError(
                f"Invalid model '{model}' "
                f"for mlx engine. "
                f"Valid: {valid}"
            )


# --------------------------------------------------------------
def load_whisper_model(model_name):
    """Load a faster-whisper model."""
    from faster_whisper import WhisperModel
    print(
        f"Loading faster-whisper "
        f"model '{model_name}'..."
    )
    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
    )
    return model


# --------------------------------------------------------------
def load_mlx_model(model_name):
    """Load a lightning-whisper-mlx model."""
    from lightning_whisper_mlx import (
        LightningWhisperMLX,
    )
    print(
        f"Loading mlx-whisper "
        f"model '{model_name}'..."
    )
    model = LightningWhisperMLX(
        model=model_name,
        batch_size=12,
        quant=None,
    )
    return model


# --------------------------------------------------------------
def get_audio_duration(audio_file):
    """Get audio duration via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries",
        "format=duration",
        "-of", "csv=p=0",
        audio_file,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return None
    val = result.stdout.strip()
    return float(val) if val else None


# --------------------------------------------------------------
def try_get_duration(audio_file):
    """Try to get duration, return None."""
    try:
        return get_audio_duration(audio_file)
    except Exception:
        return None


# --------------------------------------------------------------
def transcribe_whisper(
    model, audio_file, language="en"
):
    """Transcribe using faster-whisper."""
    print(f"Transcribing {audio_file}...")
    print(f"Language: {language}")
    segments, info = model.transcribe(
        audio_file, language=language
    )
    return segments, info


# --------------------------------------------------------------
def transcribe_mlx(
    model, audio_file, language="en"
):
    """Transcribe using lightning-whisper-mlx."""
    print(f"Transcribing {audio_file}...")
    print(f"Language: {language}")
    result = model.transcribe(
        audio_path=audio_file,
        language=language,
    )
    return result


# --------------------------------------------------------------
def format_elapsed(seconds):
    """Format seconds as HH:MM:SS."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# --------------------------------------------------------------
def format_time_now():
    """Format current wall-clock time."""
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# --------------------------------------------------------------
def calc_pct_and_eta(
    seg_end, duration, start_time
):
    """Calculate percent done and ETA."""
    if duration is None or duration <= 0:
        return None, None
    pct = min(
        seg_end / duration * 100, 100.0
    )
    elapsed = time.time() - start_time
    if pct > 0:
        total_est = elapsed / (pct / 100.0)
        remaining = total_est - elapsed
        eta_ts = time.time() + remaining
        eta_str = datetime.fromtimestamp(
            eta_ts
        ).strftime("%Y-%m-%d %H:%M:%S")
    else:
        eta_str = "unknown"
    return pct, eta_str


# --------------------------------------------------------------
def print_timing(
    seg_end, duration, start_time
):
    """Print timing info to terminal."""
    now_str = format_time_now()
    elapsed = time.time() - start_time
    elapsed_str = format_elapsed(elapsed)
    pct, eta_str = calc_pct_and_eta(
        seg_end, duration, start_time
    )
    print(f"  Wall clock:  {now_str}")
    print(f"  Elapsed:     {elapsed_str}")
    if pct is not None:
        print(f"  Progress:    {pct:.1f}%")
        print(f"  ETA:         {eta_str}")
    else:
        print("  Progress:    unknown")
        print("  ETA:         unknown")
    print()


# --------------------------------------------------------------
def make_output_path(audio_file):
    """Build output .txt path from audio."""
    p = Path(audio_file)
    return p.with_suffix(".txt")


# --------------------------------------------------------------
def process_whisper_segments(
    segments, info, duration,
    start_time, out_file
):
    """Process faster-whisper segments."""
    prob = info.language_probability
    header = (
        f"Detected language: {info.language}"
        f" (probability: {prob:.2f})"
    )
    print(f"\n{header}\n")
    print("Transcript:")
    print("-" * 65)
    chunk_count = 0
    with open(
        out_file, "w", encoding="utf-8"
    ) as f:
        f.write(header + "\n")
        f.write("=" * 60 + "\n\n")
        for segment in segments:
            text = segment.text
            print(text)
            f.write(text + "\n")
            chunk_count += 1
            if chunk_count % 10 == 0:
                print_timing(
                    segment.end,
                    duration,
                    start_time,
                )
    print("-" * 65)


# --------------------------------------------------------------
def process_mlx_result(result, out_file):
    """Process mlx-whisper result."""
    text = result.get("text", "")
    lang = result.get("language", "en")
    header = f"Detected language: {lang}"
    print(f"\n{header}\n")
    print("Transcript:")
    print("-" * 65)
    print(text)
    print("-" * 65)
    with open(
        out_file, "w", encoding="utf-8"
    ) as f:
        f.write(header + "\n")
        f.write("=" * 60 + "\n\n")
        f.write(text + "\n")


# --------------------------------------------------------------
def run_whisper(args, start_time):
    """Run transcription with faster-whisper."""
    model = load_whisper_model(args.model)
    duration = try_get_duration(
        args.audio_file
    )
    if duration:
        mins = duration / 60
        print(
            f"Audio duration: {mins:.1f} min"
        )
    segments, info = transcribe_whisper(
        model, args.audio_file,
        args.language,
    )
    out_file = make_output_path(
        args.audio_file
    )
    process_whisper_segments(
        segments, info, duration,
        start_time, out_file,
    )
    return out_file


# --------------------------------------------------------------
def run_mlx(args, start_time):
    """Run transcription with mlx-whisper."""
    model = load_mlx_model(args.model)
    duration = try_get_duration(
        args.audio_file
    )
    if duration:
        mins = duration / 60
        print(
            f"Audio duration: {mins:.1f} min"
        )
    result = transcribe_mlx(
        model, args.audio_file,
        args.language,
    )
    out_file = make_output_path(
        args.audio_file
    )
    process_mlx_result(result, out_file)
    return out_file


# --------------------------------------------------------------
def main():
    """Main function."""
    args = parse_args()
    validate_model(args.engine, args.model)
    print(
        f"Engine: {args.engine}, "
        f"Model: {args.model}, "
        f"Language: {args.language}"
    )
    start_time = time.time()
    if args.engine == "mlx":
        out_file = run_mlx(args, start_time)
    else:
        out_file = run_whisper(
            args, start_time
        )
    elapsed = time.time() - start_time
    print(
        f"\nDone! Total time: "
        f"{format_elapsed(elapsed)}"
    )
    print(
        f"Transcript saved to: {out_file}"
    )


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
