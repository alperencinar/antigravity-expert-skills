#!/bin/bash

# process_screenshots.sh - Automates resizing, converting, and renaming store screenshots using sips.
# Usage: ./process_screenshots.sh <input_dir> <output_dir> [width] [height] [format]

set -e

# Default values
INPUT_DIR=""
OUTPUT_DIR=""
WIDTH=2064
HEIGHT=2752
FORMAT="jpeg"

# Help menu
show_help() {
  echo "Usage: ./process_screenshots.sh <input_dir> <output_dir> [width] [height] [format]"
  echo ""
  echo "Arguments:"
  echo "  input_dir   Directory containing raw screenshots (PNG/JPEG)"
  echo "  output_dir  Directory where processed screenshots will be saved"
  echo "  width       Target width (default: 2064)"
  echo "  height      Target height (default: 2752)"
  echo "  format      Output format (default: jpeg)"
  echo ""
  echo "Example:"
  echo "  ./process_screenshots.sh ~/Downloads/raw ~/Downloads/ready 2064 2752 jpeg"
}

# Parse parameters
if [ "$#" -lt 2 ]; then
  show_help
  exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"

if [ -n "$3" ]; then WIDTH="$3"; fi
if [ -n "$4" ]; then HEIGHT="$4"; fi
if [ -n "$5" ]; then FORMAT="$5"; fi

# Validate directories
if [ ! -d "$INPUT_DIR" ]; then
  echo "Error: Input directory '$INPUT_DIR' does not exist."
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "=== ASO Screenshot Processor ==="
echo "Input Directory  : $INPUT_DIR"
echo "Output Directory : $OUTPUT_DIR"
echo "Target Resolution: ${WIDTH}x${HEIGHT} px"
echo "Output Format    : $FORMAT"
echo "================================"

# Check if sips is available (macOS only)
if ! command -v sips &> /dev/null; then
  echo "Error: 'sips' command line utility is not available. This script must be run on macOS."
  exit 1
fi

# Locate and process screenshots
count=0
# Find PNG or JPG/JPEG images
find "$INPUT_DIR" -maxdepth 1 -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \) | sort | while read -r img_path; do
  filename=$(basename "$img_path")
  extension="${filename##*.}"
  filename_no_ext="${filename%.*}"
  
  # Clean filename (lowercase, underscores, strip special characters)
  clean_name=$(echo "$filename_no_ext" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd 'a-z0-9_')
  
  # Prevent empty names after cleaning
  if [ -z "$clean_name" ]; then
    clean_name="screenshot"
  fi
  
  count=$((count + 1))
  # Format sequence index (e.g. 01, 02...)
  index=$(printf "%02d" $count)
  
  output_filename="${index}_${clean_name}.${FORMAT}"
  output_path="${OUTPUT_DIR}/${output_filename}"
  
  echo "Processing [${index}]: '$filename' -> '$output_filename'..."
  
  # Run sips to resize and convert format
  sips -z "$HEIGHT" "$WIDTH" -s format "$FORMAT" "$img_path" --out "$output_path" &> /dev/null
done

echo "Process completed successfully! Processed $count screenshots."
