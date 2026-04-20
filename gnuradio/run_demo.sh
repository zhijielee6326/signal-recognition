#!/bin/bash
# 毕业设计 - 视频传输系统启动脚本
# Usage:
#   ./run_demo.sh sim          # 仿真模式（无需USRP）
#   ./run_demo.sh full         # USRP实机模式
#   ./run_demo.sh sim camera   # 仿真+摄像头
#   ./run_demo.sh sim video.mp4  # 仿真+视频文件

cd "$(dirname "$0")"
PYTHON="/home/zhijielee/桌面/毕设/venv/bin/python3"

MODE="${1:-sim}"
SOURCE="${2:-test}"

echo "========================================"
echo " 面向信号干扰检测与识别的视频传输系统"
echo " 模式: $MODE  视频源: $SOURCE"
echo "========================================"

if [ "$MODE" = "full" ]; then
    # Check USRP connection
    echo "检查USRP连接..."
    if ! uhd_find_devices 2>&1 | grep -q "serial: 7MFTKFU"; then
        echo "错误: USRP未连接，请检查USB连接"
        exit 1
    fi
    echo "USRP B210 已连接"
fi

exec "$PYTHON" video_transmission_system.py --mode "$MODE" --source "$SOURCE"
