#!/usr/bin/env python3
"""Get transcript and summary for a YouTube URL."""

# Usage:
#   python yt_url_tr_sum.py <URL>
#   python yt_url_tr_sum.py --help
#
# Examples:
#   python yt_url_tr_sum.py https://youtu.be/abc123
#   python yt_url_tr_sum.py https://www.youtube.com/watch?v=abc123
#
# Output:
#   data/20260216-my_title-transcript.txt
#   data/20260216-my_title-summary.txt

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
    )
    from youtube_transcript_api.formatters import (
        TextFormatter,
    )
except ImportError:
    print(
        "Missing: uv pip install "
        "youtube-transcript-api"
    )
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("Missing: uv pip install anthropic")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("Missing: uv pip install yt-dlp")
    sys.exit(1)

try:
    from transliterate import translit
except ImportError:
    print(
        "Missing: uv pip install transliterate"
    )
    sys.exit(1)

MODEL = "claude-sonnet-4-20250514"
MAX_TRANSCRIPT_CHARS = 80_000
TITLE_MAX_LEN = 30


# --------------------------------------------------------------
def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Get transcript and summary "
            "for a YouTube video URL."
        ),
        epilog=(
            "Example: python yt_url_tr_sum.py "
            "https://youtu.be/abc123"
        ),
    )
    parser.add_argument(
        "url",
        help="YouTube video URL",
    )
    return parser.parse_args()


# --------------------------------------------------------------
def extract_video_id(url):
    """Extract video ID from a YouTube URL."""
    m = re.search(
        r"v=([A-Za-z0-9_-]{11})", url
    )
    if m:
        return m.group(1)
    m = re.search(
        r"youtu\.be/([A-Za-z0-9_-]{11})", url
    )
    if m:
        return m.group(1)
    return None


# --------------------------------------------------------------
def fetch_video_title(url):
    """Fetch video title using yt-dlp."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(
            url, download=False
        )
    return info.get("title", "untitled")


# --------------------------------------------------------------
def has_cyrillic(text):
    """Check if text has Cyrillic characters."""
    return bool(
        re.search(r'[\u0400-\u04FF]', text)
    )


# --------------------------------------------------------------
def transliterate_title(title):
    """Transliterate Russian to Latin chars."""
    if has_cyrillic(title):
        return translit(
            title, 'ru', reversed=True
        )
    return title


# --------------------------------------------------------------
def sanitize_title(title):
    """Sanitize title for use in filenames."""
    title = transliterate_title(title)
    cleaned = re.sub(
        r'[^a-zA-Z0-9]+', '_', title
    )
    cleaned = cleaned.strip('_')
    return cleaned[:TITLE_MAX_LEN].rstrip('_')


# --------------------------------------------------------------
def build_file_prefix(title):
    """Build date-title prefix for filenames."""
    date_str = datetime.now().strftime("%Y%m%d")
    safe_title = sanitize_title(title)
    return f"{date_str}-{safe_title}"


# --------------------------------------------------------------
def find_best_transcript(tlist, langs):
    """Find manual or auto-generated transcript."""
    tref = None
    try:
        tref = (
            tlist
            .find_manually_created_transcript(
                langs
            )
        )
    except Exception:
        pass
    if tref is None:
        try:
            tref = (
                tlist
                .find_generated_transcript(
                    langs
                )
            )
        except Exception:
            pass
    if tref is None:
        tref = try_translate_transcript(tlist)
    return tref


# --------------------------------------------------------------
def try_translate_transcript(tlist):
    """Try translating any available transcript."""
    for t in tlist:
        try:
            if t.language_code != "en":
                return t.translate("en")
            return t
        except Exception:
            continue
    return None


# --------------------------------------------------------------
def fetch_transcript(video_id):
    """Fetch transcript for a video ID."""
    langs = ["en", "en-US", "en-GB"]
    api = YouTubeTranscriptApi()
    tlist = api.list(video_id)
    tref = find_best_transcript(tlist, langs)
    if tref is None:
        return None
    fetched = tref.fetch()
    formatter = TextFormatter()
    plain = formatter.format_transcript(fetched)
    return plain


# --------------------------------------------------------------
def build_header(title, url):
    """Build file header with title and URL."""
    return (
        f"Title: {title}\n"
        f"Video: {url}\n"
        f"{'=' * 60}\n\n"
    )


# --------------------------------------------------------------
def save_transcript(path, title, url, text):
    """Save transcript file with header."""
    header = build_header(title, url)
    path.write_text(
        header + text + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------
def build_summary_prompt(transcript):
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
def summarize_text(transcript):
    """Call Claude to summarize the transcript."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=key)
    text = transcript
    if len(text) > MAX_TRANSCRIPT_CHARS:
        text = text[:MAX_TRANSCRIPT_CHARS]
    prompt = build_summary_prompt(text)
    response = client.messages.create(
        model=MODEL,
        max_tokens=250,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.content[0].text.strip()


# --------------------------------------------------------------
def one_sentence_per_line(text):
    """Put each sentence on its own line."""
    return re.sub(
        r"([.!?])\s+(?=[A-Z])", r"\1\n", text
    )


# --------------------------------------------------------------
def save_summary(path, title, url, summary):
    """Save summary file with header."""
    header = build_header(title, url)
    formatted = one_sentence_per_line(summary)
    path.write_text(
        header + formatted + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------
def main():
    """Main function."""
    args = parse_args()
    url = args.url
    video_id = extract_video_id(url)
    if not video_id:
        print(f"Cannot extract video ID: {url}")
        sys.exit(1)
    print(f"Fetching video info for: {url}")
    title = fetch_video_title(url)
    print(f"Title: {title}")
    prefix = build_file_prefix(title)
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    tr_path = data_dir / f"{prefix}-transcript.txt"
    sum_path = data_dir / f"{prefix}-summary.txt"
    print("Fetching transcript...", end=" ")
    transcript = fetch_transcript(video_id)
    if transcript is None:
        print("❌ No transcript available")
        sys.exit(1)
    print("✅")
    save_transcript(tr_path, title, url, transcript)
    print(f"Saved: {tr_path}")
    print("Generating summary...", end=" ")
    summary = summarize_text(transcript)
    print("✅")
    save_summary(sum_path, title, url, summary)
    print(f"Saved: {sum_path}")
    print("\nDone!")


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
