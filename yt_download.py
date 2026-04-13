#!/usr/bin/env python3
"""Download YouTube videos using yt-dlp."""

# Usage:
#   python yt_download.py <URL> [quality]
#
# Quality options:
#   low    - 480p video (small file)
#   medium - 720p video (default)
#   high   - best available quality
#   audio  - audio only (mp3)
#
# Examples:
#   python yt_download.py https://youtu.be/abc123
#   python yt_download.py https://youtu.be/abc123 low
#   python yt_download.py https://youtu.be/abc123 medium
#   python yt_download.py https://youtu.be/abc123 high
#   python yt_download.py https://youtu.be/abc123 audio
#
# Output filenames include a suffix for the mode:
#   20260214_Video_Title_audio.mp3
#   20260214_Video_Title_low.mp4
#   20260214_Video_Title_medium.mp4
#   20260214_Video_Title_high.mp4

import os
import sys
import re
import glob
import subprocess
from datetime import datetime
import yt_dlp
from transliterate import translit

QUALITY_SUFFIX = {
    "low": "_low",
    "medium": "_medium",
    "high": "_high",
    "audio": "_audio",
}

# --------------------------------------------------------------
def has_cyrillic(text):
    """Check if text contains Cyrillic characters."""
    return bool(re.search(r'[\u0400-\u04FF]', text))

# --------------------------------------------------------------
def transliterate_title(title):
    """Transliterate Russian title to Latin chars."""
    if has_cyrillic(title):
        return translit(title, 'ru', reversed=True)
    return title

# --------------------------------------------------------------
def sanitize_title(title):
    """Replace non-alphanumeric chars with underscores."""
    title = transliterate_title(title)
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '_', title)
    cleaned = cleaned.strip('_')
    cleaned = cleaned[:40].rstrip('_')
    return cleaned

# --------------------------------------------------------------
def make_output_template(quality_mode, title):
    """Build output template with date, title, and quality."""
    date_prefix = datetime.now().strftime("%Y%m%d")
    suffix = QUALITY_SUFFIX.get(quality_mode, "")
    if quality_mode == "audio":
        ext = "%(ext)s"
    else:
        ext = "mp4"
    template = (
        f"{date_prefix}_"
        f"{title}{suffix}.{ext}"
    )
    return template

# --------------------------------------------------------------
def get_common_opts(output_template):
    """Return common yt-dlp options."""
    return {
        "outtmpl": output_template,
        "quiet": False,
        "overwrites": True,
    }

# --------------------------------------------------------------
def get_postprocessors_video():
    """Return postprocessors to re-encode audio to AAC."""
    return [{
        "key": "FFmpegVideoConvertor",
        "preferedformat": "mp4",
    }]

# --------------------------------------------------------------
def get_ffmpeg_args():
    """Return ffmpeg args for AAC audio encoding."""
    return [
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
    ]

# --------------------------------------------------------------
def get_ydl_opts(quality_mode, output_template):
    """Return yt-dlp options for given quality mode."""
    common = get_common_opts(output_template)
    if quality_mode == "low":
        return {
            **common,
            "format": (
                "bestvideo[height<=480]+bestaudio"
                "/best[height<=480]/best"
            ),
            "merge_output_format": "mp4",
            "postprocessor_args": {
                "merger": get_ffmpeg_args(),
            },
        }
    if quality_mode == "medium":
        return {
            **common,
            "format": (
                "bestvideo[height<=720]+bestaudio"
                "/best[height<=720]/best"
            ),
            "merge_output_format": "mp4",
            "postprocessor_args": {
                "merger": get_ffmpeg_args(),
            },
        }
    if quality_mode == "high":
        return {
            **common,
            "format": (
                "bestvideo+bestaudio/best"
            ),
            "merge_output_format": "mp4",
            "postprocessor_args": {
                "merger": get_ffmpeg_args(),
            },
        }
    if quality_mode == "audio":
        return {
            **common,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    raise ValueError(
        f"Unknown mode: {quality_mode}"
    )

# --------------------------------------------------------------
def print_usage():
    """Print usage instructions."""
    print("Usage:")
    print("  python yt_download.py <URL> [quality]")
    print()
    print("Quality options:")
    print("  low    - 480p (small file)")
    print("  medium - 720p (default)")
    print("  high   - best available")
    print("  audio  - audio only (mp3)")
    print()
    print("Examples:")
    print("  python yt_download.py URL")
    print("  python yt_download.py URL low")
    print("  python yt_download.py URL high")
    print("  python yt_download.py URL audio")

# --------------------------------------------------------------
def find_downloaded_file(date_prefix, quality_mode):
    """Find the most recently downloaded file."""
    ext = "mp3" if quality_mode == "audio" else "mp4"
    suffix = QUALITY_SUFFIX.get(quality_mode, "")
    pattern = f"{date_prefix}_*{suffix}.{ext}"
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

# --------------------------------------------------------------
def show_file_info(filepath):
    """Show video/audio file info using vid_info."""
    vid_info = os.path.expanduser(
        "~/docs/bin/vid_info"
    )
    if os.path.isfile(vid_info):
        print()
        subprocess.run(
            [vid_info, filepath], check=False
        )
    else:
        show_basic_info(filepath)

# --------------------------------------------------------------
def show_basic_info(filepath):
    """Show basic file info as fallback."""
    size_mb = (
        os.path.getsize(filepath) / 1024 / 1024
    )
    print()
    print(f"File: {filepath}")
    print(f"File size: {size_mb:.2f} MB")

# --------------------------------------------------------------
def fetch_title(url):
    """Fetch video title without downloading."""
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("title", "video")

# --------------------------------------------------------------
def download_video(url, quality_mode="medium"):
    """Download a YouTube video with given quality."""
    date_prefix = datetime.now().strftime("%Y%m%d")
    raw_title = fetch_title(url)
    title = sanitize_title(raw_title)
    output_template = make_output_template(
        quality_mode, title
    )
    ydl_opts = get_ydl_opts(
        quality_mode, output_template
    )
    print(f"Downloading: {url}")
    print(f"Title: {raw_title}")
    print(f"Quality: {quality_mode}")
    print()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print()
    print("Download complete!")
    filepath = find_downloaded_file(
        date_prefix, quality_mode
    )
    if filepath:
        show_file_info(filepath)

# --------------------------------------------------------------
def main():
    """Main function."""
    valid = ["low", "medium", "high", "audio"]
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    url = sys.argv[1]
    if url in ("-h", "--help"):
        print_usage()
        sys.exit(0)
    quality_mode = "medium"
    if len(sys.argv) >= 3:
        quality_mode = sys.argv[2].lower()
    if quality_mode not in valid:
        print(
            f"Error: invalid quality "
            f"'{quality_mode}'"
        )
        print(f"Valid options: {valid}")
        sys.exit(1)
    download_video(url, quality_mode)

# --------------------------------------------------------------
if __name__ == "__main__":
    main()
