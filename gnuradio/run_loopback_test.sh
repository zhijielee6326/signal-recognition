#!/bin/bash
# USRP自发自收快速测试脚本

echo "========================================"
echo "USRP自发自收干扰检测快速测试"
echo "========================================"

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
echo ""

# 运行测试
echo "开始测试..."
python3 usrp_loopback_test.py \
    --serial "$SERIAL" \
    --model "$MODEL_PATH" \
    --type "$TEST_TYPE" \
    --tests "$NUM_TESTS"

echo ""
echo "测试完成！"
