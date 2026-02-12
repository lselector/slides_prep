#!/usr/bin/env python3
"""Summarize YouTube transcripts using Claude."""

import os
import re
import sys
import argparse
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing: uv pip install anthropic")
    sys.exit(1)

MODEL = "claude-sonnet-4-20250514"
MAX_TRANSCRIPT_CHARS = 80_000


# --------------------------------------------------------------
def get_client() -> anthropic.Anthropic:
    """Create Anthropic client from env key."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    return anthropic.Anthropic(api_key=key)


# --------------------------------------------------------------
def list_transcript_files(
    directory: Path,
) -> list[Path]:
    """List .txt files that are not summaries."""
    files = sorted(directory.glob("*.txt"))
    return [
        f for f in files
        if not f.name.startswith("s_")
        and "timestamped" not in f.name
    ]


# --------------------------------------------------------------
def read_transcript(filepath: Path) -> str:
    """Read transcript text from file."""
    return filepath.read_text(encoding="utf-8")


# --------------------------------------------------------------
def extract_header(text: str) -> tuple[str, str]:
    """Extract Title and Video URL from header."""
    title = ""
    url = ""
    for line in text.splitlines():
        if line.startswith("Title:"):
            title = line.strip()
        elif line.startswith("Video:"):
            url = line.strip()
        if title and url:
            break
    return title, url


# --------------------------------------------------------------
def truncate_text(text: str) -> str:
    """Truncate transcript to fit context."""
    if len(text) > MAX_TRANSCRIPT_CHARS:
        return text[:MAX_TRANSCRIPT_CHARS]
    return text


# --------------------------------------------------------------
def build_prompt(transcript: str) -> str:
    """Build the summarization prompt."""
    return (
        "Summarize the following YouTube video "
        "transcript in approximately 120-150 "
        "tokens. Write in plain text with no "
        "formatting (no markdown, no bullets, "
        "no headers). Just a concise paragraph "
        "capturing the key points and main "
        "takeaways.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )


# --------------------------------------------------------------
def summarize_text(
    client: anthropic.Anthropic,
    transcript: str,
) -> str:
    """Call Claude to summarize the transcript."""
    prompt = build_prompt(
        truncate_text(transcript)
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=250,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.content[0].text.strip()


# --------------------------------------------------------------
def one_sentence_per_line(text: str) -> str:
    """Put each sentence on its own line."""
    return re.sub(
        r"([.!?])\s+(?=[A-Z])", r"\1\n", text
    )


# --------------------------------------------------------------
def make_summary_dir(
    transcript_dir: Path,
) -> Path:
    """Create summary dir under data/."""
    name = transcript_dir.name + "-Summaries"
    out_dir = Path("data") / name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


# --------------------------------------------------------------
def already_summarized(
    summary_dir: Path, filename: str
) -> bool:
    """Check if summary file already exists."""
    return (summary_dir / f"s_{filename}").exists()


# --------------------------------------------------------------
def save_summary(
    out_path: Path,
    title: str,
    url: str,
    summary: str,
) -> None:
    """Save summary with header to file."""
    formatted = one_sentence_per_line(summary)
    content = f"{title}\n{url}\n\n{formatted}\n"
    out_path.write_text(
        content, encoding="utf-8"
    )


# --------------------------------------------------------------
def process_one_file(
    client, filepath, summary_dir
) -> bool:
    """Summarize one transcript file."""
    text = read_transcript(filepath)
    title, url = extract_header(text)
    summary = summarize_text(client, text)
    out_path = summary_dir / f"s_{filepath.name}"
    save_summary(out_path, title, url, summary)
    return True


# --------------------------------------------------------------
def process_directory(
    directory: Path, force: bool = False
) -> None:
    """Process all transcripts in directory."""
    client = get_client()
    files = list_transcript_files(directory)
    summary_dir = make_summary_dir(directory)
    if not files:
        print("No transcript files found.")
        return
    print(f"Found {len(files)} transcripts")
    print(f"Output dir: {summary_dir}\n")
    success, skipped, failed = 0, 0, 0
    for filepath in files:
        title, _ = extract_header(
            filepath.read_text(encoding="utf-8")
        )
        label = title[:50] if title else filepath.name
        if not force and already_summarized(
            summary_dir, filepath.name
        ):
            print(f"  [SKIP] {label}")
            skipped += 1
            continue
        print(
            f"  Summarizing: {label}...",
            end=" ",
            flush=True,
        )
        try:
            process_one_file(
                client, filepath, summary_dir
            )
            print("✅")
            success += 1
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            failed += 1
    print(f"\n{'=' * 50}")
    print(
        f"Done! {success} summarized, "
        f"{skipped} skipped, {failed} failed"
    )


# --------------------------------------------------------------
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Summarize transcripts"
    )
    parser.add_argument(
        "directory",
        help="Directory with transcript files",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Re-summarize existing files",
    )
    args = parser.parse_args()
    d = Path(args.directory)
    if not d.is_dir():
        print(f"Not a directory: {d}")
        sys.exit(1)
    process_directory(d, force=args.force)


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
