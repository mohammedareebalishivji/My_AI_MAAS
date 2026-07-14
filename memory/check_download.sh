#!/bin/bash
SIZE=$(stat -f%z ~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz 2>/dev/null || echo 0)
TOTAL=83256934
if [ "$SIZE" -eq 0 ]; then
  echo "Download not started yet."
elif [ "$SIZE" -ge "$TOTAL" ]; then
  echo "Download complete! ($(echo "scale=2; $SIZE/1048576" | bc) MB)"
  echo "Run: python memory/init_db.py  (from memory/ or with venv active)"
else
  PCT=$(echo "scale=1; $SIZE*100/$TOTAL" | bc)
  echo "Progress: $PCT% ($(echo "scale=1; $SIZE/1048576" | bc) MB / $(echo "scale=1; $TOTAL/1048576" | bc) MB)"
fi
