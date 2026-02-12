#!/usr/bin/env python3
"""Extract transcripts from YouTube channel videos."""

import argparse
import json
import re
import subprocess
import sys
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
def build_channel_url(channel: str) -> str:
    """Build YouTube channel URL from input."""
    if channel.startswith("@"):
        return (
            f"https://www.youtube.com"
            f"/{channel}/videos"
        )
    if "youtube.com" in channel:
        return channel
    return (
        f"https://www.youtube.com"
        f"/@{channel}/videos"
    )


# --------------------------------------------------------------
def run_ytdlp(url: str, count: int) -> str:
    """Run yt-dlp and return stdout."""
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        f"--playlist-end={count}",
        "--print",
        "%(id)s|||%(title)s"
        "|||%(upload_date)s"
        "|||%(duration)s",
        "--no-warnings",
        url,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        print("yt-dlp not found: pip install yt-dlp")
        sys.exit(1)
    if result.returncode != 0:
        print(f"yt-dlp error:\n{result.stderr}")
        sys.exit(1)
    return result.stdout


# --------------------------------------------------------------
def parse_video_line(line: str) -> dict | None:
    """Parse one yt-dlp output line into a dict."""
    parts = line.split("|||")
    if len(parts) < 2:
        return None
    return {
        "id": parts[0].strip(),
        "title": parts[1].strip(),
        "upload_date": (
            parts[2].strip()
            if len(parts) > 2 else "unknown"
        ),
        "duration": (
            parts[3].strip()
            if len(parts) > 3 else "unknown"
        ),
    }


# --------------------------------------------------------------
def get_channel_videos(
    channel: str, count: int = 7
) -> list[dict]:
    """Get latest videos from a YouTube channel."""
    url = build_channel_url(channel)
    print(
        f"Fetching last {count} videos "
        f"from: {url}"
    )
    stdout = run_ytdlp(url, count)
    videos = []
    for line in stdout.strip().splitlines():
        v = parse_video_line(line)
        if v:
            videos.append(v)
    return videos


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
    """Format transcript into plain and timestamped."""
    fetched = tref.fetch()
    formatter = TextFormatter()
    plain = formatter.format_transcript(fetched)
    timestamped = build_timestamped(fetched)
    return {
        "plain": plain,
        "timestamped": timestamped,
        "type": tref.language,
        "is_generated": tref.is_generated,
    }


# --------------------------------------------------------------
def build_timestamped(fetched) -> str:
    """Build timestamped text from fetched data."""
    lines = []
    for snippet in fetched:
        start = snippet.start
        text = snippet.text
        mins, secs = divmod(int(start), 60)
        hours, mins = divmod(mins, 60)
        ts = f"{hours:02d}:{mins:02d}:{secs:02d}"
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines)


# --------------------------------------------------------------
def get_transcript(video_id: str) -> dict | None:
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
def sanitize_filename(name: str) -> str:
    """Remove unsafe characters from filename."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:100]


# --------------------------------------------------------------
def format_date(date: str) -> str:
    """Format YYYYMMDD date to YYYY-MM-DD."""
    if date and date != "unknown" and len(date) == 8:
        return (
            f"{date[:4]}-{date[4:6]}-{date[6:]}"
        )
    return date


# --------------------------------------------------------------
def print_video_list(videos: list[dict]):
    """Print numbered list of found videos."""
    print(f"\nFound {len(videos)} videos:\n")
    for i, v in enumerate(videos, 1):
        date = format_date(v["upload_date"])
        print(
            f"  {i}. [{date}] {v['title']}"
            f"  (ID: {v['id']})"
        )


# --------------------------------------------------------------
def build_header(
    title: str, vid_id: str,
    upload_date: str, lang_info: str
) -> str:
    """Build file header for transcript."""
    url = (
        "https://www.youtube.com"
        f"/watch?v={vid_id}"
    )
    return (
        f"Title: {title}\n"
        f"Video: {url}\n"
        f"Date: {upload_date}\n"
        f"Transcript type: {lang_info}\n"
        f"{'=' * 60}\n\n"
    )


# --------------------------------------------------------------
def save_plain(
    out_dir, safe_name, header, text
):
    """Save plain transcript file."""
    fpath = out_dir / f"{safe_name}.txt"
    fpath.write_text(
        header + text + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------
def save_timestamped(
    out_dir, safe_name, header, text
):
    """Save timestamped transcript file."""
    fname = f"{safe_name} [timestamped].txt"
    fpath = out_dir / fname
    fpath.write_text(
        header + text + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------
def save_transcript_files(
    out_dir, i, video, result, fmt
):
    """Save transcript to files per format."""
    title = video["title"]
    vid_id = video["id"]
    lang_info = (
        "auto-generated"
        if result["is_generated"]
        else "manual"
    )
    safe_name = sanitize_filename(
        f"{i:02d} - {title}"
    )
    header = build_header(
        title, vid_id,
        video["upload_date"], lang_info,
    )
    if fmt in ("plain", "both"):
        save_plain(
            out_dir, safe_name,
            header, result["plain"],
        )
    if fmt in ("timestamped", "both"):
        save_timestamped(
            out_dir, safe_name,
            header, result["timestamped"],
        )
    return lang_info


# --------------------------------------------------------------
def process_one_video(
    i, video, total, out_dir, fmt
):
    """Process a single video transcript."""
    vid_id = video["id"]
    title = video["title"]
    label = f"[{i}/{total}] {title}..."
    print(label, end=" ", flush=True)
    result = get_transcript(vid_id)
    if result is None:
        print("❌ No transcript available")
        video["transcript"] = None
        video["transcript_error"] = (
            "No transcript available"
        )
        return video
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        video["transcript"] = None
        video["transcript_error"] = (
            result["error"]
        )
        return video
    lang_info = save_transcript_files(
        out_dir, i, video, result, fmt,
    )
    print(f"✅ ({lang_info})")
    video["transcript"] = result["plain"]
    video["transcript_timestamped"] = (
        result["timestamped"]
    )
    video["transcript_type"] = lang_info
    return video


# --------------------------------------------------------------
def process_all_videos(
    videos, out_dir, fmt
):
    """Extract transcripts for all videos."""
    print("\n--- Extracting transcripts ---\n")
    all_results = []
    total = len(videos)
    for i, video in enumerate(videos, 1):
        v = process_one_video(
            i, video, total, out_dir, fmt,
        )
        all_results.append(v)
    return all_results


# --------------------------------------------------------------
def save_combined_json(
    out_dir, all_results
):
    """Save combined JSON with all transcripts."""
    json_path = out_dir / "all_transcripts.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            all_results, f,
            indent=2, ensure_ascii=False,
        )
    print(f"\nCombined JSON saved to: {json_path}")


# --------------------------------------------------------------
def print_summary(all_results, out_dir):
    """Print final summary of results."""
    success = sum(
        1 for v in all_results
        if v.get("transcript")
    )
    failed = len(all_results) - success
    total = len(all_results)
    print(f"\n{'=' * 60}")
    print(
        f"Done! {success}/{total} "
        f"transcripts extracted."
    )
    if failed:
        print(
            f"({failed} video(s) had "
            f"no transcript available)"
        )
    print(f"Output directory: {out_dir.resolve()}")


# --------------------------------------------------------------
def build_arg_parser():
    """Build argument parser with all options."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract YouTube channel "
            "transcripts"
        ),
    )
    parser.add_argument(
        "--channel",
        default="@AllAboutAI",
        help="Channel handle, name, or URL",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=7,
        help="Number of videos (default: 7)",
    )
    parser.add_argument(
        "--output",
        default="data/transcripts",
        help="Output dir (default: data/transcripts)",
    )
    return parser


# --------------------------------------------------------------
def add_format_args(parser):
    """Add format and json arguments."""
    parser.add_argument(
        "--format",
        choices=[
            "plain", "timestamped", "both",
        ],
        default="both",
        help="Transcript format (default: both)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also save combined JSON file",
    )


# --------------------------------------------------------------
def parse_args():
    """Parse command line arguments."""
    parser = build_arg_parser()
    add_format_args(parser)
    return parser.parse_args()


# --------------------------------------------------------------
def main():
    """Main entry point."""
    args = parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    videos = get_channel_videos(
        args.channel, args.count,
    )
    if not videos:
        print("No videos found.")
        sys.exit(1)
    print_video_list(videos)
    all_results = process_all_videos(
        videos, out_dir, args.format,
    )
    if args.json:
        save_combined_json(out_dir, all_results)
    print_summary(all_results, out_dir)


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
