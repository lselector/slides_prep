#!/usr/bin/env python3
"""Transcribe MP3 audio files to text."""

# Usage:
#   python transcribe_mp3_to_txt.py <audio_file.mp3>
#   python transcribe_mp3_to_txt.py --help
#
# Description:
#   Transcribes an MP3 audio file to text
#   using the faster-whisper model.
#   Uses the "medium" model on CPU
#   with int8 compute type.
#
# Output:
#   Also saves transcript to a .txt file
#   with the same name as the audio file.
#
# Example:
#   python transcribe_mp3_to_txt.py my_recording.mp3
#   => creates my_recording.txt

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

from faster_whisper import WhisperModel


# --------------------------------------------------------------
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe an MP3 audio file "
            "to text using faster-whisper."
        ),
        epilog=(
            "Example: python "
            "transcribe_mp3_to_txt.py rec.mp3"
        ),
    )
    parser.add_argument(
        "audio_file",
        help="Path to the MP3 file",
    )
    return parser.parse_args()


# --------------------------------------------------------------
def load_model():
    """Load the Whisper model."""
    print("Loading Whisper model...")
    model = WhisperModel(
        "medium",
        device="cpu",
        compute_type="int8",
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
    """Try to get duration, return None on fail."""
    try:
        return get_audio_duration(audio_file)
    except Exception:
        return None


# --------------------------------------------------------------
def transcribe_audio(model, audio_file):
    """Transcribe an MP3 file to text."""
    print(f"Transcribing {audio_file}...")
    segments, info = model.transcribe(
        audio_file, language="en"
    )
    return segments, info


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
    pct = min(seg_end / duration * 100, 100.0)
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
    """Build output .txt path from audio path."""
    p = Path(audio_file)
    return p.with_suffix(".txt")


# --------------------------------------------------------------
def process_segments(
    segments, info, duration, start_time,
    out_file
):
    """Process segments: print + write to file."""
    prob = info.language_probability
    header = (
        f"Detected language: {info.language}"
        f" (probability: {prob:.2f})"
    )
    print(f"\n{header}\n")
    print("Transcript:")
    print("-" * 65)
    chunk_count = 0
    with open(out_file, "w", encoding="utf-8") as f:
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
def main():
    """Main function."""
    args = parse_args()
    start_time = time.time()
    model = load_model()
    duration = try_get_duration(
        args.audio_file
    )
    if duration:
        mins = duration / 60
        print(
            f"Audio duration: {mins:.1f} min"
        )
    segments, info = transcribe_audio(
        model, args.audio_file
    )
    out_file = make_output_path(args.audio_file)
    process_segments(
        segments, info, duration,
        start_time, out_file,
    )
    elapsed = time.time() - start_time
    print(
        f"\nDone! Total time: "
        f"{format_elapsed(elapsed)}"
    )
    print(f"Transcript saved to: {out_file}")


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
