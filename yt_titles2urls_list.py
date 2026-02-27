#!/usr/bin/env python3
"""Find YouTube video URLs by title using yt-dlp."""

import re
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yt_dlp

DEFAULT_INPUT = "data/20260212-titles.txt"
DEFAULT_OUTPUT = "data/20260212-URLs.txt"


# --------------------------------------------------------------
def build_ydl_opts() -> dict:
    """Build yt-dlp options for search."""
    return {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "default_search": "ytsearch",
        "noplaylist": True,
    }


# --------------------------------------------------------------
def get_cutoff_date(max_age_days: int) -> str:
    """Get cutoff date string YYYYMMDD."""
    dt = datetime.now(
        timezone.utc
    ) - timedelta(days=max_age_days)
    return dt.strftime("%Y%m%d")


# --------------------------------------------------------------
def search_youtube_video(
    title: str,
    max_results: int = 5,
    max_age_days: int = 14,
) -> str | None:
    """Search YouTube for a recent video."""
    cutoff = get_cutoff_date(max_age_days)
    query = f"ytsearch{max_results}:{title}"
    opts = build_ydl_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(
                query, download=False,
            )
        except Exception as exc:
            print(
                f"  [ERROR] search failed: {exc}",
                file=sys.stderr,
            )
            return None
    if not info or "entries" not in info:
        return None
    return find_recent_entry(info, cutoff)


# --------------------------------------------------------------
def find_recent_entry(info, cutoff) -> str | None:
    """Find first entry newer than cutoff."""
    for entry in info["entries"]:
        if entry is None:
            continue
        upload = entry.get("upload_date", "")
        if upload and upload >= cutoff:
            vid = entry.get("id")
            if vid:
                return (
                    "https://www.youtube.com"
                    f"/watch?v={vid}"
                )
    return None


# --------------------------------------------------------------
def parse_titles_file(
    filepath: str,
) -> list[tuple[int, str]]:
    """Parse numbered or plain titles file."""
    results = []
    counter = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            num, rest = parse_one_line(line)
            if rest is None:
                continue
            if num is None:
                counter += 1
                num = counter
            if rest == "...":
                continue
            rest = re.sub(
                r"\s*\[\d+:\d+(:\d+)?\]\s*$",
                "", rest,
            )
            results.append((num, rest))
    return results


# --------------------------------------------------------------
def parse_one_line(line: str):
    """Parse one line, numbered or plain."""
    m = re.match(r"^(\d+)\.\s+(.+)", line)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, line


# --------------------------------------------------------------
def search_all_titles(
    titles, max_age_days,
) -> list[tuple[int, str, str]]:
    """Search YouTube for all titles."""
    results = []
    for num, title in titles:
        print(f"[{num}] Searching: {title}")
        url = search_youtube_video(
            title, max_age_days=max_age_days,
        )
        if url:
            print(f"     => {url}")
            results.append((num, title, url))
        else:
            print("     => NOT FOUND")
            results.append(
                (num, title, "NOT FOUND"),
            )
    return results


# --------------------------------------------------------------
def write_results(
    output_path: str,
    results: list[tuple[int, str, str]],
) -> None:
    """Write search results to output file."""
    Path(output_path).parent.mkdir(
        parents=True, exist_ok=True,
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"YouTube URLs - Generated {now}\n")
        f.write("=" * 60 + "\n\n")
        for num, title, url in results:
            short = shorten_title(title)
            f.write(f"{num}. {short}\n")
            f.write(f"   {url}\n\n")
    print(f"\nResults saved to {output_path}")


# --------------------------------------------------------------
def shorten_title(title: str) -> str:
    """Shorten title by removing channel info."""
    if " — " in title:
        return title.split(" — ")[0].strip()
    return title


# --------------------------------------------------------------
def handle_single_title(args) -> None:
    """Handle single title search mode."""
    print(f"Searching for: {args.title}")
    url = search_youtube_video(
        args.title, max_age_days=args.days,
    )
    if url:
        print(f"  Found: {url}")
    else:
        print("  Not found (or too old)")


# --------------------------------------------------------------
def output_from_input(fpath: str) -> str:
    """Derive output path from input path."""
    return fpath.replace("titles", "URLs")


# --------------------------------------------------------------
def handle_file_mode(args) -> None:
    """Handle file-based search mode."""
    fpath = args.input or DEFAULT_INPUT
    if not Path(fpath).exists():
        print(f"File not found: {fpath}")
        sys.exit(1)
    titles = parse_titles_file(fpath)
    print(
        f"Parsed {len(titles)} titles "
        f"from {fpath}\n"
    )
    results = search_all_titles(
        titles, args.days,
    )
    out = args.output or output_from_input(fpath)
    write_results(out, results)


# --------------------------------------------------------------
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find YouTube URLs by title",
    )
    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT,
        help="Input titles file",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output URLs file",
    )
    parser.add_argument(
        "--title", "-t",
        help="Single title to search for",
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=14,
        help="Max age in days (default 14)",
    )
    return parser.parse_args()


# --------------------------------------------------------------
def main():
    """Main entry point."""
    args = parse_args()
    if args.title:
        handle_single_title(args)
    else:
        handle_file_mode(args)


# --------------------------------------------------------------
if __name__ == "__main__":
    main()
