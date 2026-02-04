#!/bin/bash
# =============================================================================
# S2DR4 Super-Resolution Setup for WSL2 + NVIDIA GPU
# Run this script INSIDE your WSL2 terminal
# =============================================================================
set -e

echo "============================================"
echo "S2DR4 WSL2 Setup"
echo "============================================"

# 1. Check NVIDIA GPU is accessible from WSL
echo ""
echo "[1/5] Checking NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo "  GPU detected OK"
else
    echo "  ERROR: nvidia-smi not found!"
    echo "  Make sure you have:"
    echo "    - NVIDIA GPU driver installed on Windows"
    echo "    - WSL2 (not WSL1)"
    echo "    - Latest Windows NVIDIA driver (supports WSL CUDA)"
    echo "  See: https://docs.nvidia.com/cuda/wsl-user-guide/"
    exit 1
fi

# 2. Check Python version
echo ""
echo "[2/5] Checking Python..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "  $PYTHON_VERSION"

# Check if Python 3.12 (required by the wheel)
if python3 -c "import sys; assert sys.version_info[:2] == (3,12)" 2>/dev/null; then
    echo "  Python 3.12 OK"
    PYTHON=python3
else
    echo "  WARNING: S2DR4 wheel requires Python 3.12"
    echo "  Installing Python 3.12 via deadsnakes PPA..."
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.12 python3.12-venv python3.12-dev
    PYTHON=python3.12
fi

# 3. Create virtual environment
echo ""
echo "[3/5] Creating virtual environment..."
VENV_DIR="$HOME/s2dr4_env"
if [ -d "$VENV_DIR" ]; then
    echo "  Removing existing venv..."
    rm -rf "$VENV_DIR"
fi
$PYTHON -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

# 4. Install S2DR4
echo ""
echo "[4/5] Installing S2DR4 package..."
pip install https://storage.googleapis.com/0x7ff601307fa5/s2dr4-20260126.1-cp312-cp312-linux_x86_64.whl

# 5. Create output directory
echo ""
echo "[5/5] Creating output directory..."
OUTPUT_DIR="$HOME/s2dr4_output"
mkdir -p "$OUTPUT_DIR"

echo ""
echo "============================================"
echo "SETUP COMPLETE!"
echo "============================================"
echo ""
echo "To run inference, activate the env and run:"
echo "  source $VENV_DIR/bin/activate"
echo "  python /mnt/d/Udemy_Cour/Gamma\\ Earth\\ S2DR4/run_s2dr4.py"
echo ""
