#!/usr/bin/env bash
set -euo pipefail

# Google Meet Attendance Analysis Runner
# This script runs the complete analysis pipeline from the repo directory

echo "🎓 Google Meet Attendance & Engagement Analysis"
echo "==============================================="

# Determine workspace: repository root (parent of scripts dir) by default
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
WORKSPACE="${WORKSPACE:-$ROOT_DIR}"
cd "$WORKSPACE"
# Force UTF-8 output so emoji/status text won't crash on Windows codepages.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

echo "📁 Working directory: $WORKSPACE"
echo ""

PYTHON_BIN=""
PYTHON_ARGS=()
if [ -x "/c/Windows/py.exe" ]; then
  PYTHON_BIN="/c/Windows/py.exe"
  PYTHON_ARGS=(-3)
elif [ -x "/mnt/c/Windows/py.exe" ]; then
  PYTHON_BIN="/mnt/c/Windows/py.exe"
  PYTHON_ARGS=(-3)
elif command -v py >/dev/null 2>&1; then
  PYTHON_BIN="py"
  PYTHON_ARGS=(-3)
elif command -v python3 >/dev/null 2>&1 && ! command -v python3 | rg -i "WindowsApps" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1 && ! command -v python | rg -i "WindowsApps" >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "❌ Error: Python 3 is required but not installed (no python3/py/python found)."
  exit 1
fi

run_python() {
  "$PYTHON_BIN" "${PYTHON_ARGS[@]}" "$@"
}

# Count the number of transcript and chat files (support folders or flat layout)
if [ -d transcripts ]; then
  TRANSCRIPT_COUNT=$(ls -1 transcripts/*' - Transcript.txt' 2>/dev/null | wc -l || true)
else
  TRANSCRIPT_COUNT=$(ls -1 *' - Transcript.txt' 2>/dev/null | wc -l || true)
fi

if [ -d chats ]; then
  CHAT_COUNT=$(ls -1 chats/*' - Chat' 2>/dev/null | wc -l || true)
else
  CHAT_COUNT=$(ls -1 *' - Chat' 2>/dev/null | wc -l || true)
fi

echo "📄 Found $TRANSCRIPT_COUNT transcript files and $CHAT_COUNT chat files"

if [ "${TRANSCRIPT_COUNT:-0}" -eq 0 ]; then
    echo "❌ No transcript files found. Please ensure your Google Meet files are in this directory."
    echo "   Expected filename format: 'Enterprise Web Development - C1 - YYYY_MM_DD HH_MM CAT - Transcript.txt'"
    exit 1
fi

echo ""
echo "🔄 Running attendance analysis..."

# Run the main analysis
if run_python improved_attendance_tracker.py --workspace "$WORKSPACE" --output "$WORKSPACE/data/attendance_report.json" --summary; then
    echo ""
    echo "✅ Analysis complete! Generated files:"
    echo "   📊 data/attendance_report.json - Complete data"
    echo "   🌐 index.html - Interactive dashboard"
    echo ""
    
    echo "🔍 Generating detailed summary..."
    echo ""
    
    # Run the summary report
    run_python summary_report.py --workspace "$WORKSPACE"
    
    echo ""
    echo "🌐 View the dashboard (serving locally avoids browser file restrictions):"
    echo "   $PYTHON_BIN ${PYTHON_ARGS[*]} -m http.server 8000"
    echo "   Then open: http://localhost:8000/index.html"
    echo ""
    
    echo "📤 To export data:"
    echo "   - Use the 'Export Full Report' button in the dashboard"
    echo "   - Or copy data/attendance_report.json for external analysis"
    echo ""
    
    echo "✨ Analysis complete! Check the summary above for key insights."
    
else
    echo "❌ Error running analysis. Please check the error messages above."
    exit 1
fi
