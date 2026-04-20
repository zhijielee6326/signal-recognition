#!/bin/bash
# USRP天线对天线测试脚本（无需衰减器）

echo "========================================"
echo "USRP天线对天线干扰检测测试"
echo "========================================"
echo ""
echo "⚠️  注意：请确保两个天线已连接到USRP的TX/RX和RX2端口"
echo "         天线之间保持适当距离（建议10-50cm）"
echo ""

# 检查虚拟环境
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  虚拟环境未激活，正在激活..."
    source ~/毕设/venv/bin/activate
fi

# 检查USRP设备
echo "检查USRP设备..."
if ! uhd_find_devices > /dev/null 2>&1; then
    echo "❌ 未找到USRP设备！"
    echo "请检查："
    echo "  1. USRP是否连接"
    echo "  2. 用户是否在usrp组中: groups | grep usrp"
    exit 1
fi
echo "✓ USRP设备已连接"

# 检查模型文件
MODEL_PATH="../CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth"
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ 模型文件不存在: $MODEL_PATH"
    exit 1
fi
echo "✓ 模型文件存在"

# 设置默认参数
SERIAL="${USRP_SERIAL:-serial=7MFTKFU}"
TEST_TYPE="${1:-all}"
NUM_TESTS="${2:-10}"

echo ""
echo "测试配置:"
echo "  USRP序列号: $SERIAL"
echo "  测试类型: $TEST_TYPE"
echo "  测试次数: $NUM_TESTS"
echo "  连接方式: 天线对天线（无衰减器）"
echo "  TX增益: 10 dB (降低功率)"
echo "  RX增益: 40 dB (提高灵敏度)"
echo ""
echo "按Enter继续，或Ctrl+C取消..."
read

# 运行测试
echo "开始测试..."
python3 usrp_loopback_test.py \
    --serial "$SERIAL" \
    --model "$MODEL_PATH" \
    --type "$TEST_TYPE" \
    --tests "$NUM_TESTS"

echo ""
echo "测试完成！"
