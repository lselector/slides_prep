#!/usr/bin/env python3
"""Summarize a text file using Claude."""

# Usage:
#   python summarize.py <text_file.txt>
#   python summarize.py --help
#
# Description:
#   Reads a text file and generates a
#   concise summary using Claude API.
#   Saves the summary as a new file with
#   "_summary" appended to the base name.
#
# Output:
#   Creates <basename>_summary.txt in the
#   same directory as the input file.
#
# Example:
#   python summarize.py data/mytext.txt
#   => creates data/mytext_summary.txt

import os
import re
import sys
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    print(
        "Missing: uv pip install anthropic"
    )
    sys.exit(1)

MODEL = "claude-sonnet-4-20250514"
MAX_TRANSCRIPT_CHARS = 80_000


# --------------------------------------------------------------
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Summarize a text file "
            "using Claude API."
        ),
        epilog=(
            "Example: python summarize.py "
            "data/mytext.txt"
        ),
    )
    parser.add_argument(
        "text_file",
        help="Path to the text file",
    )
    return parser.parse_args()


# --------------------------------------------------------------
def get_client():
    """Create Anthropic client from env key."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    return anthropic.Anthropic(api_key=key)


# --------------------------------------------------------------
def read_text_file(filepath):
    """Read text content from file."""
    p = Path(filepath)
    if not p.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


# --------------------------------------------------------------
def truncate_text(text):
    """Truncate text to fit context window."""
    if len(text) > MAX_TRANSCRIPT_CHARS:
        return text[:MAX_TRANSCRIPT_CHARS]
    return text


# --------------------------------------------------------------
def build_prompt(text):
    """Build the summarization prompt."""
    return (
        "Summarize the following text in "
        "approximately 120-150 tokens. "
        "Write in plain text with no "
        "formatting (no markdown, no bullets, "
        "no headers). Just a concise paragraph "
        "capturing the key points and main "
        "takeaways.\n\n"
        f"TEXT:\n{text}"
    )


# --------------------------------------------------------------
def summarize_text(client, text):
    """Call Claude to summarize the text."""
    prompt = build_prompt(
        truncate_text(text)
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=250,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    return response.content[0].text.strip()


# --------------------------------------------------------------
def one_sentence_per_line(text):
    """Put each sentence on its own line."""
    return re.sub(
        r"([.!?])\s+(?=[A-Z])",
        r"\1\n",
        text,
    )


# --------------------------------------------------------------
def make_output_path(input_path):
    """Build output path with _summary suffix."""
    p = Path(input_path)
    stem = p.stem
    return p.parent / f"{stem}_summary.txt"


# --------------------------------------------------------------
def save_summary(out_path, summary):
    """Save formatted summary to file."""
    formatted = one_sentence_per_line(summary)
    out_path.write_text(
        formatted + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------
def main():
    """Main function."""
    args = parse_args()
    input_path = args.text_file
    print(f"Reading: {input_path}")
    text = read_text_file(input_path)
    print(f"Text length: {len(text)} chars")
    client = get_client()
    print("Generating summary...", end=" ")
    summary = summarize_text(client, text)
    print("✅")
    out_path = make_output_path(input_path)
    save_summary(out_path, summary)
    print(f"Saved: {out_path}")
    print("\nDone!")


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
