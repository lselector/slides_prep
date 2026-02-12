#!/bin/bash

# Script: get_weather.sh
# Purpose: Use Claude Code to fetch current temperature for zip code 10040

# Configuration
ZIP_CODE="10040"
OUTPUT_FILE="temperature_${ZIP_CODE}.txt"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Create the prompt for Claude
PROMPT="Go to a weather website and find the current temperature for zip code ${ZIP_CODE}. Return only the temperature value with the unit (e.g., '45°F' or '7°C')."

# Execute Claude Code in print mode (-p flag means query once and exit)
echo "Fetching weather data for zip code ${ZIP_CODE}..."

claude --allowed-tools "WebSearch WebFetch" \
       --permission-mode dontAsk \
       -p "$PROMPT" > temp_output.txt 2>&1

# Check if command was successful
if [ $? -eq 0 ]; then
    # Extract the temperature and save with timestamp
    echo "=== Weather Data for ZIP ${ZIP_CODE} ===" > "$OUTPUT_FILE"
    echo "Retrieved: ${TIMESTAMP}" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    cat temp_output.txt >> "$OUTPUT_FILE"
    
    echo "✓ Temperature saved to ${OUTPUT_FILE}"
    
    # Display the result
    echo ""
    echo "Current temperature:"
    cat temp_output.txt
else
    echo "✗ Error: Failed to fetch weather data"
    cat temp_output.txt
    exit 1
fi

# Cleanup temporary file
rm -f temp_output.txt


