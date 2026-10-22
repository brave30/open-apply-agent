#!/usr/bin/env bash
# Keep the complete runtime on shared data storage; never use home for caches.
set -euo pipefail
OPEN_APPLY_ROOT=${OPEN_APPLY_ROOT:-/data01/tmalekar/open-apply}
source "$OPEN_APPLY_ROOT/env.sh"
cd "$OPEN_APPLY_ROOT/app"
GPU_UUID=GPU-b9defd43-7472-55d9-ed1f-271f39c3e878
exec 9>"$OPEN_APPLY_ROOT/logs/gpu0.lock"
flock -n 9 || { echo 'Another Open Apply run holds GPU 0.' >&2; exit 42; }
# The lock coordinates our runs. Other users do not share it, so also inspect NVML.
active=$(nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader)
if grep -Fxq "$GPU_UUID" <<< "$active"; then
  echo 'GPU 0 has an active compute process; refusing to start.' >&2
  exit 42
fi
used=$(nvidia-smi -i "$GPU_UUID" --query-gpu=memory.used --format=csv,noheader,nounits)
if [ "$used" -gt 256 ]; then
  echo "GPU 0 uses ${used} MiB; refusing to start." >&2
  exit 42
fi
nvidia-smi --query-gpu=index,uuid,name,memory.used,utilization.gpu --format=csv
export CUDA_VISIBLE_DEVICES=$GPU_UUID
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
python -m auto_apply.cli agent --output "$OPEN_APPLY_ROOT/artifacts" "$@"
