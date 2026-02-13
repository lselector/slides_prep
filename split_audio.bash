#!/bin/bash

# splits audio file into 3 pieces
# usage: bash split_audio.bash myaudio.mp3

# Check if filename argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <audio_file.mp3>"
    exit 1
fi

audio_file="$1"
base_name="${audio_file%.mp3}"

# Check if file exists
if [ ! -f "$audio_file" ]; then
    echo "Error: File '$audio_file' not found"
    exit 1
fi

# Get the duration
duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$audio_file")

# Calculate segment length (duration / 3)
segment_time=$(python -c "print($duration / 3)")

echo "Splitting $audio_file (${duration}s) into 3 segments of ~${segment_time}s each..."

# Split into 3 parts
ffmpeg -i "$audio_file" -t $segment_time -c copy "${base_name}_part1.mp3"
ffmpeg -i "$audio_file" -ss $segment_time -t $segment_time -c copy "${base_name}_part2.mp3"
ffmpeg -i "$audio_file" -ss $(python -c "print($segment_time * 2)") -c copy "${base_name}_part3.mp3"

echo "Done! Created: ${base_name}_part1.mp3, ${base_name}_part2.mp3, ${base_name}_part3.mp3"
