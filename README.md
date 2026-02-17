# slides_prep

Python and Bash scripts for downloading YouTube videos,
extracting transcripts, generating summaries, transcribing audio,
and fetching AI leaderboard data.

---

## Table of Contents

- [get_weather.bash](#get_weatherbash)
- [leaderboard.py](#leaderboardpy)
- [split_audio.bash](#split_audiobash)
- [summarize.py](#summarizepy)
- [transcribe_mp3_to_txt.py](#transcribe_mp3_to_txtpy)
- [yt_download.py](#yt_downloadpy)
- [yt_titles2urls_list.py](#yt_titles2urls_listpy)
- [yt_tr2summary_list.py](#yt_tr2summary_listpy)
- [yt_tr_channel.py](#yt_tr_channelpy)
- [yt_tr_list.py](#yt_tr_listpy)
- [yt_url_tr_sum.py](#yt_url_tr_sumpy)

---

## get_weather.bash

Fetch current temperature for a zip code using Claude CLI.

```bash
bash get_weather.bash
```

- **Input:** ZIP code is hardcoded in the script (default: `12741`). Edit `ZIP_CODE` variable to change it.
- **Output:** `data/temperature_<ZIP_CODE>.txt` — contains the temperature with a timestamp.
- **Requires:** Claude CLI installed and configured.

---

## leaderboard.py

Fetch the top 25 models from Arena AI leaderboards and save to Excel.

```bash
python leaderboard.py
```

- **Input:** None (URLs are hardcoded).
- **Output:**
  - `leaderboard_text.xlsx` — top 25 from the text leaderboard.
  - `leaderboard_text_coding.xlsx` — top 25 from the coding leaderboard.
- **Details:** Model names are clickable hyperlinks. Rows are color-coded by vendor (Anthropic=blue, Google=red, OpenAI=gold, open-source=green).
- **Requires:** `pip install openpyxl`

---

## split_audio.bash

Split an MP3 audio file into 3 equal parts.

```bash
bash split_audio.bash <audio_file.mp3>
```

- **Input:** Path to an MP3 file.
- **Output:** Three files in the same directory:
  - `<name>_part1.mp3`
  - `<name>_part2.mp3`
  - `<name>_part3.mp3`
- **Requires:** `ffmpeg` and `ffprobe` installed.

---

## summarize.py

Generate a short summary of a text file using the Claude API.

```bash
python summarize.py <text_file.txt>
```

- **Input:** Path to any text file.
- **Output:** `<basename>_summary.txt` in the same directory as the input file. Contains a plain-text paragraph (120-150 tokens), one sentence per line.
- **Requires:** `pip install anthropic`. Environment variable `ANTHROPIC_API_KEY` must be set.

---

## transcribe_mp3_to_txt.py

Transcribe an MP3 audio file to text using the faster-whisper model.

```bash
python transcribe_mp3_to_txt.py <audio_file.mp3>
```

- **Input:** Path to an MP3 file.
- **Output:** `<name>.txt` (same name as the audio file, with `.txt` extension). Shows progress with elapsed time, percent done, and ETA during transcription.
- **Requires:** `pip install faster-whisper`. Also needs `ffprobe` installed.

---

## yt_download.py

Download a YouTube video or extract audio using yt-dlp.

```bash
python yt_download.py <URL> [quality]
```

- **Input:**
  - `URL` — YouTube video URL.
  - `quality` (optional) — one of `low` (480p), `medium` (720p, default), `high` (best), `audio` (MP3 only).
- **Output:** File in the current directory named `YYYYMMDD_<title>_<quality>.mp4` (or `.mp3` for audio mode). Cyrillic titles are transliterated to Latin.
- **Requires:** `pip install yt-dlp transliterate`. Also needs `ffmpeg` installed.

---

## yt_titles2urls_list.py

Search YouTube for video URLs by title. Can process a file of titles or search for a single title.

```bash
# From a titles file
python yt_titles2urls_list.py -i data/titles.txt -o data/urls.txt

# Single title search
python yt_titles2urls_list.py -t "Some Video Title"
```

- **Input (file mode):** A text file with numbered titles, e.g.:
  ```
  1. My First Video Title
  2. Another Video [12:34]
  ```
  Duration suffixes like `[12:34]` are stripped automatically.
- **Input (single mode):** A title string via `--title` / `-t`.
- **Options:**
  - `-i` / `--input` — input titles file (default: `data/20260212-titles.txt`).
  - `-o` / `--output` — output URLs file (default: `data/20260212-URLs.txt`).
  - `-d` / `--days` — max video age in days (default: 14).
- **Output:** A text file with numbered titles and their YouTube URLs.
- **Requires:** `pip install yt-dlp`

---

## yt_tr2summary_list.py

Summarize all transcript files in a directory using the Claude API.

```bash
python yt_tr2summary_list.py <directory>
python yt_tr2summary_list.py <directory> --force
```

- **Input:** A directory containing `.txt` transcript files (as produced by `yt_tr_list.py` or `yt_tr_channel.py`). Files starting with `s_` or containing `timestamped` are skipped.
- **Options:**
  - `--force` / `-f` — re-summarize files that already have summaries.
- **Output:** Creates a `data/<dirname>-Summaries/` directory with summary files named `s_<original_name>.txt`. Each summary includes the video title, URL, and a plain-text paragraph.
- **Requires:** `pip install anthropic`. Environment variable `ANTHROPIC_API_KEY` must be set.

---

## yt_tr_channel.py

Extract transcripts from the latest videos of a YouTube channel.

```bash
python yt_tr_channel.py --channel @ChannelName --count 10
```

- **Input:** YouTube channel handle, name, or URL.
- **Options:**
  - `--channel` — channel handle like `@AllAboutAI` (default: `@AllAboutAI`).
  - `--count` — number of recent videos to process (default: 7).
  - `--output` — output directory (default: `data/transcripts`).
  - `--format` — `plain`, `timestamped`, or `both` (default: `both`).
  - `--json` — also save a combined `all_transcripts.json` file.
- **Output:** One or two `.txt` files per video in the output directory:
  - `<NN> - <title>.txt` — plain transcript.
  - `<NN> - <title> [timestamped].txt` — transcript with `[HH:MM:SS]` timestamps.
- **Requires:** `pip install yt-dlp youtube-transcript-api`

---

## yt_tr_list.py

Extract transcripts from a list of YouTube URLs in a file.

```bash
python yt_tr_list.py <input_file>
```

- **Input:** A `.txt` or `.json` file with YouTube URLs.
  - **Text format** — numbered list with URLs on the next line:
    ```
    1. Video Title
       https://www.youtube.com/watch?v=abc123
    ```
  - **JSON format** — `{"title": "url", ...}` dictionary.
- **Output:** Creates `data/<input_stem>/` directory with one `.txt` file per video, each containing a header (title, URL, transcript type) followed by the transcript text.
- **Requires:** `pip install youtube-transcript-api`

---

## yt_url_tr_sum.py

Get both transcript and summary for a single YouTube video URL.

```bash
python yt_url_tr_sum.py <URL>
```

- **Input:** A YouTube video URL (supports `youtube.com/watch?v=...` and `youtu.be/...` formats).
- **Output:** Two files in the `data/` directory:
  - `data/YYYYMMDD-<title>-transcript.txt` — full transcript with header.
  - `data/YYYYMMDD-<title>-summary.txt` — Claude-generated summary (120-150 tokens, one sentence per line).
- **Requires:** `pip install yt-dlp youtube-transcript-api anthropic transliterate`. Environment variable `ANTHROPIC_API_KEY` must be set.
