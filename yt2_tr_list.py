#!/usr/bin/env python3
"""Extract transcripts from a list of YouTube URLs."""

import re
import sys
import json
import argparse
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
        "Missing: pip install "
        "youtube-transcript-api"
    )
    sys.exit(1)


# --------------------------------------------------------------
def parse_urls_file(filepath: str) -> list[dict]:
    """Parse URLs file into list of video dicts."""
    videos = []
    lines = Path(filepath).read_text(
        encoding="utf-8"
    ).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            url = ""
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if "youtube.com" in next_line:
                    url = next_line
                    i += 1
            if url and "NOT FOUND" not in url:
                vid_id = extract_video_id(url)
                if vid_id:
                    videos.append({
                        "num": num,
                        "title": title,
                        "url": url,
                        "id": vid_id,
                    })
        i += 1
    return videos


# --------------------------------------------------------------
def parse_json_file(filepath: str) -> list[dict]:
    """Parse JSON file into list of video dicts."""
    text = Path(filepath).read_text(
        encoding="utf-8"
    )
    data = json.loads(text)
    videos = []
    for num, (title, url) in enumerate(
        data.items(), start=1
    ):
        vid_id = extract_video_id(url)
        if vid_id:
            videos.append({
                "num": num,
                "title": title,
                "url": url,
                "id": vid_id,
            })
    return videos


# --------------------------------------------------------------
def parse_input_file(filepath: str) -> list[dict]:
    """Auto-detect format and parse input file."""
    if filepath.endswith(".json"):
        return parse_json_file(filepath)
    return parse_urls_file(filepath)


# --------------------------------------------------------------
def extract_video_id(url: str) -> str | None:
    """Extract video ID from a YouTube URL."""
    m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


# --------------------------------------------------------------
def sanitize_filename(name: str) -> str:
    """Keep only alphanumeric chars and underscores."""
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    name = name.strip("_")
    return name[:80]


# --------------------------------------------------------------
def make_output_dir(filepath: str) -> Path:
    """Create output dir under data/."""
    stem = Path(filepath).stem
    out_dir = Path("data") / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


# --------------------------------------------------------------
def fetch_transcript(video_id: str) -> dict | None:
    """Fetch transcript for a single video."""
    langs = ["en", "en-US", "en-GB"]
    try:
        api = YouTubeTranscriptApi()
        tlist = api.list(video_id)
        tref = find_best_transcript(tlist, langs)
        if tref is None:
            return None
        return format_transcript(tref)
    except Exception as e:
        return {"error": str(e)}


# --------------------------------------------------------------
def find_best_transcript(tlist, langs):
    """Find manual or auto-generated transcript."""
    tref = None
    try:
        tref = (
            tlist
            .find_manually_created_transcript(langs)
        )
    except Exception:
        pass
    if tref is None:
        try:
            tref = (
                tlist
                .find_generated_transcript(langs)
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
def format_transcript(tref) -> dict:
    """Format transcript into plain text."""
    fetched = tref.fetch()
    formatter = TextFormatter()
    plain = formatter.format_transcript(fetched)
    is_gen = tref.is_generated
    lang = tref.language
    return {
        "plain": plain,
        "type": lang,
        "is_generated": is_gen,
    }


# --------------------------------------------------------------
def save_transcript(
    out_dir, num, title, video, result
):
    """Save transcript file to output directory."""
    safe = sanitize_filename(
        f"{num:02d}_{title}"
    )
    url = video["url"]
    lang_info = (
        "auto-generated"
        if result["is_generated"]
        else "manual"
    )
    header = (
        f"Title: {title}\n"
        f"Video: {url}\n"
        f"Transcript type: {lang_info}\n"
        f"{'=' * 60}\n\n"
    )
    out_path = out_dir / f"{safe}.txt"
    out_path.write_text(
        header + result["plain"] + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------
def process_videos(videos, out_dir):
    """Process all videos and extract transcripts."""
    success = 0
    failed = 0
    total = len(videos)
    for video in videos:
        num = video["num"]
        title = video["title"]
        vid_id = video["id"]
        label = f"[{num}] {title[:50]}"
        print(f"{label}...", end=" ", flush=True)
        result = fetch_transcript(vid_id)
        if result is None:
            print("❌ No transcript")
            failed += 1
            continue
        if "error" in result:
            print(f"❌ {result['error'][:40]}")
            failed += 1
            continue
        print("✅")
        save_transcript(
            out_dir, num, title, video, result
        )
        success += 1
    return success, failed, total


# --------------------------------------------------------------
def print_summary(success, failed, total, out_dir):
    """Print final summary."""
    print(f"\n{'=' * 50}")
    print(
        f"Done! {success}/{total} transcripts "
        f"extracted."
    )
    if failed:
        print(f"({failed} had no transcript)")
    print(f"Output: {out_dir.resolve()}")


# --------------------------------------------------------------
def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract transcripts from URL list"
    )
    parser.add_argument(
        "input_file",
        help="File with YouTube URLs (.json or .txt)",
    )
    args = parser.parse_args()
    fpath = args.input_file
    if not Path(fpath).exists():
        print(f"File not found: {fpath}")
        sys.exit(1)
    videos = parse_input_file(fpath)
    if not videos:
        print("No valid URLs found in file.")
        sys.exit(1)
    out_dir = make_output_dir(fpath)
    print(
        f"Found {len(videos)} videos. "
        f"Output dir: {out_dir}\n"
    )
    success, failed, total = process_videos(
        videos, out_dir
    )
    print_summary(success, failed, total, out_dir)


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
