#!/bin/bash
# 合并分块渲染结果，并用主音轨替换音频（音画零漂移）
# 用法：bash merge_chunks.sh <prefix> <chunks> <workdir> <audio> <out_mp4>
#
# 关键点：先 `-f concat -c copy -an` 只拼视频流，再把整条 final.mp3 挂回去。
# 这样不会因为各块音频长度差导致音画累积偏移；代价是块边界可能丢 1~2 帧
# （全片约 7 帧 / 0.23s，肉眼不可见），属于可接受损耗。
set -eu

SK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="${PPTW_PROJECT:-$SK/project}"

PREFIX=${1:?prefix}
N=${2:?chunks}
WD=${3:?workdir}
AUDIO=${4:?audio}
OUT=${5:?out}

LIST="$WD/concat_${PREFIX}.txt"
: > "$LIST"
for ((k=0;k<N;k++)); do
  f="$PROJ/out/${PREFIX}_p$k.mp4"
  [ -f "$f" ] || { echo "[x] 缺少分块：$f"; exit 1; }
  echo "file '$f'" >> "$LIST"
done

echo "== 1) 视频流无损拼接"
ffmpeg -y -v error -f concat -safe 0 -i "$LIST" -an -c:v copy "$WD/${PREFIX}_video.mp4"

echo "== 2) 并入主音轨"
ffmpeg -y -v error -i "$WD/${PREFIX}_video.mp4" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest "$OUT"

echo "== 3) 体检（帧数 / 视频时长 / 音频时长）"
ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=nb_read_frames,r_frame_rate -of csv=p=0 "$OUT"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUDIO"
ls -la "$OUT"
