#!/usr/bin/env python3
"""Transcribe audio or video files to text."""

# Usage:
#   python transcribe_mp3_to_txt.py <input>
#   python transcribe_mp3_to_txt.py -d 2:00 talk.mp4
#   python transcribe_mp3_to_txt.py -e mlx rec.mp3
#   python transcribe_mp3_to_txt.py -m medium rec.mp3
#   python transcribe_mp3_to_txt.py -l fr rec.mp3
#   python transcribe_mp3_to_txt.py \
#       --initial-prompt "Muse Spark Meta" t.mp4
#   python transcribe_mp3_to_txt.py --help
#
# Description:
#   Transcribes an audio or video file to text.
#   Output is YouTube-style: short text lines
#   (<= 40 chars) prepended with timestamps
#   (M:SS or H:MM:SS).
#
#   Accepted inputs:
#     Audio: mp3, wav, m4a, flac, ogg, opus, aac
#     Video: mp4, mov, mkv, avi, webm, m4v
#   Video files have their audio extracted via
#   ffmpeg to a temporary mp3 next to the input
#   (<name>.extracted.mp3); the temp is removed
#   after transcription.
#
# Engines (-e/--engine):
#   - "whisper" (default): faster-whisper on CPU
#     with int8. More accurate; tuned to avoid
#     dropping spans (condition_on_previous_text
#     off, no_speech_threshold lowered, compres-
#     sion-ratio / log-prob skipping disabled).
#     Supports --initial-prompt for biasing
#     proper nouns / jargon.
#   - "mlx": lightning-whisper-mlx, faster on
#     Apple Silicon but drops content more often
#     and exposes no tuning knobs.
#
# Models (-m/--model, default: large-v3):
#   tiny, base, small, medium, large-v3.
#   MLX also supports distil-* and other large
#   variants. Smaller models are faster but
#   miss/mishear more words. First run with a
#   given model triggers a one-time download.
#
# Duration limit (-d/--duration):
#   Only transcribe the first N of the input.
#   Accepts ffmpeg time syntax: '120' (seconds),
#   '2:00' (M:SS), or '0:02:00' (H:MM:SS). When
#   set, ffmpeg trims to a temp mp3 that gets
#   cleaned up after transcription. Useful for
#   quick test runs.
#
# Language (-l/--language, default: en):
#   ISO 639-1 codes. Examples: en (English),
#   fr (French), es (Spanish), de (German),
#   ru (Russian), ja (Japanese).
#
# Initial prompt (--initial-prompt):
#   Optional vocabulary-biasing string passed to
#   the decoder (faster-whisper only; ignored by
#   mlx). Useful for proper nouns whisper has
#   never seen, e.g. new product/brand names.
#
# Output:
#   Saves transcript to a .txt file with the
#   same base name as the *original* input
#   (e.g. talk.mp4 -> talk.txt).
#
# Examples:
#   python transcribe_mp3_to_txt.py rec.mp3
#   python transcribe_mp3_to_txt.py talk.mp4
#   python transcribe_mp3_to_txt.py -d 2:00 t.mp4
#   python transcribe_mp3_to_txt.py -e mlx t.mp4
#   python transcribe_mp3_to_txt.py -m medium t.mp4
#   python transcribe_mp3_to_txt.py -l fr a.mp3
#   python transcribe_mp3_to_txt.py \
#       --initial-prompt "Muse Spark Meta" t.mp4

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

VIDEO_EXTS = {
    ".mp4", ".mov", ".mkv", ".avi",
    ".webm", ".m4v",
}

# Standard Whisper audio constants used to
# convert lightning-whisper-mlx mel-frame seek
# values to seconds: 160 / 16000 = 0.01 s/frame.
WHISPER_SAMPLE_RATE = 16000
WHISPER_HOP_LENGTH = 160

# Max characters per timestamped chunk line.
CHUNK_MAX_CHARS = 40

WHISPER_MODELS = [
    "tiny", "base", "small", "medium",
    "large", "large-v2", "large-v3",
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
        help=(
            "Path to an audio (mp3, wav, m4a, "
            "flac, ogg, opus, aac) or video "
            "(mp4, mov, mkv, avi, webm, m4v) "
            "file."
        ),
    )
    parser.add_argument(
        "-m", "--model",
        default="large-v3",
        help=(
            "Model size: tiny, base, small, "
            "medium, large-v3 (default). MLX "
            "also supports distil-* and other "
            "large variants. Smaller = faster "
            "but more dropped/missed words."
        ),
    )
    parser.add_argument(
        "--initial-prompt",
        default=None,
        help=(
            "Optional prompt biasing vocabulary "
            "(faster-whisper only; ignored by "
            "mlx engine). Useful for names, "
            "jargon, acronyms."
        ),
    )
    parser.add_argument(
        "-d", "--duration",
        default=None,
        help=(
            "Only transcribe the first N of the "
            "input. Accepts ffmpeg time syntax: "
            "'120' (seconds), '2:00' (M:SS), or "
            "'0:02:00' (H:MM:SS). Useful for "
            "quick test runs."
        ),
    )
    parser.add_argument(
        "-e", "--engine",
        default="whisper",
        choices=["whisper", "mlx"],
        help=(
            "Engine: whisper (faster-whisper "
            "on CPU, default — more accurate, "
            "supports tuning knobs) or mlx "
            "(lightning-whisper-mlx, faster on "
            "Apple Silicon but drops content "
            "more often and exposes no tuning)."
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
def is_video_file(path):
    """True if path has a video extension."""
    return Path(path).suffix.lower() in VIDEO_EXTS


# --------------------------------------------------------------
def prepare_audio_input(input_path, duration=None):
    """Run ffmpeg if needed; return audio path.

    Returns (audio_path, temp_path_or_None).
    The caller deletes temp_path if non-None.

    ffmpeg is invoked when the input is video
    OR a duration limit is requested. Both
    cases produce a temp mp3 next to the input
    (<name>.extracted.mp3) so transcription
    sees a plain audio file.
    """
    is_video = is_video_file(input_path)
    if not is_video and duration is None:
        return input_path, None

    src = Path(input_path)
    out = src.with_suffix(".extracted.mp3")
    if is_video and duration:
        action = (
            f"Extracting + trimming "
            f"to {duration}"
        )
    elif is_video:
        action = "Extracting audio from video"
    else:
        action = f"Trimming to {duration}"
    print(f"{action}: {src.name} -> {out.name}")

    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "4",
        str(out),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed:\n"
            f"{result.stderr}"
        )
    return str(out), str(out)


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
    model, audio_file,
    language="en", initial_prompt=None,
):
    """Transcribe using faster-whisper.

    Uses settings tuned to avoid dropping
    spans of audio (a common whisper failure
    mode):
      - condition_on_previous_text=False
        prevents drift / cascading skips.
      - no_speech_threshold=0.2 (vs default
        0.6) keeps borderline-confidence
        speech instead of treating it as
        silence.
      - compression_ratio_threshold=None and
        log_prob_threshold=None disable the
        whole-window dropping that whisper
        does when a window looks "weird".
    """
    print(f"Transcribing {audio_file}...")
    print(f"Language: {language}")
    segments, info = model.transcribe(
        audio_file,
        language=language,
        initial_prompt=initial_prompt,
        condition_on_previous_text=False,
        no_speech_threshold=0.2,
        compression_ratio_threshold=None,
        log_prob_threshold=None,
        beam_size=5,
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
def format_ts(seconds):
    """Format seconds as M:SS or H:MM:SS.

    Matches the YouTube-style format shown in
    examples (e.g. 0:02, 12:34, 1:02:03).
    """
    if seconds is None or seconds < 0:
        seconds = 0
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# --------------------------------------------------------------
def split_into_chunks(text, max_chars):
    """Split text into <= max_chars chunks.

    Breaks on word boundaries. A single word
    longer than max_chars is kept intact (so
    the chunk may exceed max_chars in that
    rare case rather than splitting a word).
    """
    text = text.strip()
    if not text:
        return []
    chunks = []
    current = ""
    for word in text.split():
        if not current:
            current = word
            continue
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks


# --------------------------------------------------------------
def chunks_with_timestamps(
    start, end, text,
    max_chars=CHUNK_MAX_CHARS,
):
    """Split a segment into timestamped chunks.

    Distributes the segment's [start, end] time
    across chunks proportionally to chunk char
    length. Returns list of (timestamp_seconds,
    chunk_text).
    """
    chunks = split_into_chunks(text, max_chars)
    if not chunks:
        return []
    total_len = sum(len(c) for c in chunks)
    duration = max(0.0, (end or start) - start)
    if total_len == 0 or duration == 0:
        return [(start, c) for c in chunks]
    out = []
    consumed = 0
    for c in chunks:
        ts = start + duration * (
            consumed / total_len
        )
        out.append((ts, c))
        consumed += len(c)
    return out


# --------------------------------------------------------------
def write_timestamped(f, ts, text):
    """Write 'M:SS\\ntext\\n' to file + stdout."""
    stamp = format_ts(ts)
    print(stamp)
    print(text)
    f.write(stamp + "\n")
    f.write(text + "\n")


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
            for ts, text in chunks_with_timestamps(
                segment.start,
                segment.end,
                segment.text,
            ):
                write_timestamped(f, ts, text)
            chunk_count += 1
            if chunk_count % 10 == 0:
                print_timing(
                    segment.end,
                    duration,
                    start_time,
                )
    print("-" * 65)


# --------------------------------------------------------------
def mlx_seek_to_seconds(seek):
    """Convert mlx mel-frame seek to seconds."""
    return (
        float(seek)
        * WHISPER_HOP_LENGTH
        / WHISPER_SAMPLE_RATE
    )


# --------------------------------------------------------------
def process_mlx_result(result, out_file):
    """Process mlx-whisper result."""
    lang = result.get("language", "en")
    header = f"Detected language: {lang}"
    print(f"\n{header}\n")
    print("Transcript:")
    print("-" * 65)
    segments = result.get("segments") or []
    with open(
        out_file, "w", encoding="utf-8"
    ) as f:
        f.write(header + "\n")
        f.write("=" * 60 + "\n\n")
        if segments:
            for seg in segments:
                # mlx returns [start_seek,
                # end_seek, text] in mel-frames.
                start_seek, end_seek, text = (
                    seg[0], seg[1], seg[2]
                )
                start = mlx_seek_to_seconds(
                    start_seek
                )
                end = mlx_seek_to_seconds(
                    end_seek
                )
                for ts, chunk in chunks_with_timestamps(
                    start, end, text,
                ):
                    write_timestamped(
                        f, ts, chunk
                    )
        else:
            # Fallback: no segment timing —
            # write plain text with a 0:00 stamp.
            text = result.get("text", "")
            for chunk in split_into_chunks(
                text, CHUNK_MAX_CHARS
            ):
                write_timestamped(f, 0, chunk)
    print("-" * 65)


# --------------------------------------------------------------
def run_whisper(
    audio_file, out_file,
    model_name, language, start_time,
    initial_prompt=None,
):
    """Run transcription with faster-whisper."""
    model = load_whisper_model(model_name)
    duration = try_get_duration(audio_file)
    if duration:
        mins = duration / 60
        print(
            f"Audio duration: {mins:.1f} min"
        )
    segments, info = transcribe_whisper(
        model, audio_file, language,
        initial_prompt=initial_prompt,
    )
    process_whisper_segments(
        segments, info, duration,
        start_time, out_file,
    )
    return out_file


# --------------------------------------------------------------
def run_mlx(
    audio_file, out_file,
    model_name, language, start_time,
):
    """Run transcription with mlx-whisper."""
    model = load_mlx_model(model_name)
    duration = try_get_duration(audio_file)
    if duration:
        mins = duration / 60
        print(
            f"Audio duration: {mins:.1f} min"
        )
    result = transcribe_mlx(
        model, audio_file, language,
    )
    process_mlx_result(result, out_file)
    return out_file


# --------------------------------------------------------------
def main():
    """Main function."""
    args = parse_args()
    validate_model(args.engine, args.model)

    original_input = args.audio_file
    out_file = make_output_path(original_input)

    audio_file, temp_audio = prepare_audio_input(
        original_input,
        duration=args.duration,
    )

    print(
        f"Engine: {args.engine}, "
        f"Model: {args.model}, "
        f"Language: {args.language}"
    )
    start_time = time.time()
    try:
        if args.engine == "mlx":
            run_mlx(
                audio_file, out_file,
                args.model, args.language,
                start_time,
            )
        else:
            run_whisper(
                audio_file, out_file,
                args.model, args.language,
                start_time,
                initial_prompt=(
                    args.initial_prompt
                ),
            )
    finally:
        if temp_audio and os.path.exists(
            temp_audio
        ):
            os.remove(temp_audio)
            print(
                f"Removed temp audio: "
                f"{temp_audio}"
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
