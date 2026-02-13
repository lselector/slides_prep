#!/usr/bin/env python3
"""Transcribe MP3 audio files to text."""

# Usage:
#   python mp3_to_txt.py <audio_file.mp3>
#   python mp3_to_txt.py --help
#
# Description:
#   Transcribes an MP3 audio file to text
#   using the faster-whisper model.
#   Uses the "medium" model on CPU
#   with int8 compute type.
#
# Example:
#   python mp3_to_txt.py my_recording.mp3

import argparse
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
            "Example: "
            "python mp3_to_txt.py recording.mp3"
        ),
    )
    parser.add_argument(
        "audio_file",
        help="Path to the MP3 file to transcribe",
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
def transcribe_audio(model, audio_file):
    """Transcribe an MP3 file to text."""
    print(f"Transcribing {audio_file}...")
    segments, info = model.transcribe(
        audio_file, language="en"
    )
    return segments, info

# --------------------------------------------------------------
def print_transcript(segments, info):
    """Print the transcription results."""
    prob = info.language_probability
    print(
        f"\nDetected language: {info.language}"
        f" (probability: {prob:.2f})\n"
    )
    print("Transcript:")
    print("-" * 65)
    for segment in segments:
        print(segment.text)
    print("-" * 65)

# --------------------------------------------------------------
def main():
    """Main function."""
    args = parse_args()
    model = load_model()
    segments, info = transcribe_audio(
        model, args.audio_file
    )
    print_transcript(segments, info)

# --------------------------------------------------------------
if __name__ == "__main__":
    main()
