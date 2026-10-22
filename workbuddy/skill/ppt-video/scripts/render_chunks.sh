#!/bin/bash
# 分块渲染（断点续跑）：bash render_chunks.sh <props> <total_frames> [chunks] [prefix]
#
# 为什么必须分块：整片动辄 3~4 万帧、40~70 分钟，一次跑完一旦被中断就全丢。
# 分块后每块 ~10 分钟，重跑时「输出已存在就跳过」，只补没跑完的那一块。
#
# 环境变量（都可选）：
#   PPTW_PROJECT  指定 Remotion 工程目录（默认 <skill>/project）
#   PPTW_PY       指定 python 解释器（默认 C:/Python313/python.exe → python3）
set -u

SK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="${PPTW_PROJECT:-$SK/project}"
if [ -n "${PPTW_PY:-}" ]; then PY="$PPTW_PY"
elif [ -x "C:/Python313/python.exe" ]; then PY="C:/Python313/python.exe"
else PY="python3"; fi
RENDER="$SK/scripts/render.py"

PROPS=${1:?用法: render_chunks.sh <props> <total_frames> [chunks] [prefix]}
TOTAL=${2:?需要总帧数}
N=${3:-4}
PREFIX=${4:-chunk}

# props 必须在工程目录下（render.py 以工程目录为 cwd 传给 remotion）
case "$PROPS" in
  /*|[A-Za-z]:*)
    if [ -f "$PROPS" ] && [ "$(cd "$(dirname "$PROPS")" && pwd)" != "$(cd "$PROJ" && pwd)" ]; then
      cp -f "$PROPS" "$PROJ/" && PROPS="$(basename "$PROPS")" && echo "[i] props 已复制到工程目录：$PROPS"
    fi;;
esac

STEP=$(( (TOTAL + N - 1) / N ))
mkdir -p "$PROJ/out"

for ((k=0;k<N;k++)); do
  S=$(( k*STEP )); E=$(( S+STEP-1 ))
  [ $E -ge $TOTAL ] && E=$((TOTAL-1))
  [ $S -gt $E ] && continue
  OUT="$PROJ/out/${PREFIX}_p$k.mp4"
  if [ -f "$OUT" ]; then echo "[skip] $PREFIX 块$k 已存在"; continue; fi
  echo "[run ] $PREFIX 块$k 帧 $S-$E"
  "$PY" "$RENDER" --out "out/${PREFIX}_p$k.mp4" --props="$PROPS" \
      --concurrency=12 --frames=$S-$E >> "chunk_${PREFIX}.log" 2>&1
  rc=$?
  echo "[done] 块$k rc=$rc"
  if [ $rc -ne 0 ]; then
    echo "[!!] 块$k 失败，末尾日志："
    tail -6 "chunk_${PREFIX}.log"
  fi
done
echo ALLCHUNKS_DONE
