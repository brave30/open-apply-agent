#!/usr/bin/env bash
# Context3 runtime paths. Source this; do not place model/cache files in home.
export OPEN_APPLY_ROOT=/data01/tmalekar/open-apply
export HF_HOME=$OPEN_APPLY_ROOT/cache/huggingface
# This is where the verified checkpoint was downloaded on the shared data disk.
export HF_HUB_CACHE=/data01/tmalekar/cache/huggingface/hub
export PIP_CACHE_DIR=$OPEN_APPLY_ROOT/cache/pip
export TORCH_HOME=$OPEN_APPLY_ROOT/cache/torch
export TRITON_CACHE_DIR=$OPEN_APPLY_ROOT/cache/triton
export XDG_CACHE_HOME=$OPEN_APPLY_ROOT/cache/xdg
export XDG_CONFIG_HOME=$OPEN_APPLY_ROOT/config
export XDG_DATA_HOME=$OPEN_APPLY_ROOT/data
export XDG_STATE_HOME=$OPEN_APPLY_ROOT/state
export TMPDIR=$OPEN_APPLY_ROOT/tmp
export PLAYWRIGHT_BROWSERS_PATH=$OPEN_APPLY_ROOT/cache/browsers
export PYTHONPYCACHEPREFIX=$OPEN_APPLY_ROOT/cache/pycache
export CUDA_CACHE_PATH=$OPEN_APPLY_ROOT/cache/cuda
export TORCH_EXTENSIONS_DIR=$OPEN_APPLY_ROOT/cache/torch-extensions
export TORCHINDUCTOR_CACHE_DIR=$OPEN_APPLY_ROOT/cache/inductor
export NUMBA_CACHE_DIR=$OPEN_APPLY_ROOT/cache/numba
export MPLCONFIGDIR=$OPEN_APPLY_ROOT/cache/matplotlib
export HISTFILE=/dev/null
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8
export OPENWEBRL_MODEL=OpenWebRL/OpenWebRL-9B-SFT
export OPENWEBRL_MODEL_REVISION=4398ade320ea15660c2dfc125973232ea8bd33c7
export PATH=$OPEN_APPLY_ROOT/venv/bin:$PATH
