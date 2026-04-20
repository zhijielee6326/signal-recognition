# 快速环境与运行说明（Ubuntu + USRP）

概览：该项目包含用于训练与推理的 PyTorch 实现（位于 `CCNN/3_scripts/training/CCNN.py`），以及用于 Ascend (.om) 推理的脚本（`CCNN/3_scripts/inference/Infer.py`）。

目标：在 Ubuntu（GNURadio+UHD 已安装）中完成从 USRP 采样到 CCNN 推理的端到端验证。

1) 安装 Python 依赖（建议使用虚拟环境）

```bash
# 若尚未创建虚拟环境，可在工作区根目录创建
python3 -m venv ~/毕设/venv
# 激活环境（注意路径为工作区根的 venv）
source ~/毕设/venv/bin/activate
pip install -r CCNN/requirements.txt

# 后续每次只需在任意目录运行以下命令激活环境：
#   source ~/毕设/venv/bin/activate

# GNURadio 脚本所在路径
# 所有与 USRP 相关的脚本位于:
#   ~/毕设/gnuradio/video_transmitter.py
#   ~/毕设/gnuradio/signal_receiver.py
# 确保从该目录或通过绝对路径调用它们。

# UHD/pyUHD 绑定

USRP Python 接口 (`import uhd`) 由 Ettus 的 pyUHD 包提供。它依赖于系统级的 UHD 驱动库。

> ⚠️ **权限提醒**
> 安装 UHD 时会创建一个 `usrp` 组并安装相应的 udev 规则 (60-uhd-host.rules).
> 非 root 用户需要加入该组并重新登录 / 重新插拔设备才能访问 USRP 硬件. 运行
>
> ```bash
> sudo usermod -a -G usrp $USER
> sudo udevadm control --reload-rules && sudo udevadm trigger
> ```
>
> 如果尚未加入，`uhd_find_devices` 或 Python 中的 `uhd.usrp.MultiUSRP()`
> 会显示 “No UHD Devices Found”，尽管 `lsusb` 能看到硬件。
> 作为临时措施可以用 `sudo` 运行脚本。

Ubuntu 20.04 等较新版本默认仓库里可能没有 Python 绑定，因此请按照下列步骤安装：

1. **添加 Ettus 官方 PPA 并安装 UHD**

```bash
sudo add-apt-repository ppa:ettusresearch/uhd
sudo apt-get update
sudo apt-get install -y libuhd-dev uhd-host

# 安装完成后确保你的用户在 usrp 组中：
sudo usermod -a -G usrp $USER
# 重新加载规则并重插 USRP 或登出/登录一次：
sudo udevadm control --reload-rules && sudo udevadm trigger

# UHD 镜像目录
#
# 另外 UWHD 在启动时需要知道固件/FPGA 图像的位置；系统包
# 通常将它们放在 `/usr/share/uhd/images`。如果你看到如下警告或
# `uhd_find_devices` 输出“No UHD Devices Found”，请先设定环境变量：
#
#   export UHD_IMAGES_DIR=/usr/share/uhd/images
#
# 可以将此行添加到 `~/.bashrc` 或启动脚本，或者在调用接收/发送
# 脚本前在同一个 shell 里执行。示例：
#
#   UHD_IMAGES_DIR=/usr/share/uhd/images python3 gnuradio/signal_receiver.py …

```

上述命令会提供 `libuhd` 库和命令行工具（`uhd_find_devices` 等）。

2. **在 Python 虚拟环境中安装 pyUHD**

```bash
source ~/毕设/venv/bin/activate
# 更新打包工具
pip install --upgrade pip setuptools wheel

# 有两个常见选项：
# 1. 直接用 pip 从 GitHub 安装（需要事先在系统中安装 git）。
#    如果你的虚拟环境隔离了系统包，这通常是最可靠的方式。
# 2. 如果已经使用 apt 安装了 `python3-uhd`，也可以通过允许虚拟环境访问
#    系统 site-packages 来使用它（见下文）。

# （a）从源码构建：
# 确保先执行 `sudo apt install git` 以便能从 GitHub 拉取源码。
# 如果尚未在虚拟环境中安装过 uhd 绑定，你有两种稳妥的选择：
#
# 1. **重建 venv 并允许访问系统 site‑packages。** 这样可以直接使用
#    已通过 apt 安装的 `python3-uhd` 模块，不需再从 GitHub 拉取。
#
#       deactivate
#       python3 -m venv --system-site-packages ~/毕设/venv
#       source ~/毕设/venv/bin/activate
#       pip install -r CCNN/requirements.txt
#
#    之后 `import uhd` 就会在虚拟环境中可用。
#
# 2. **手动克隆 pyuhd 仓库然后安装。** 有时 pip 在 clone 公有仓库时会
#    弹出认证提示（如上面的“Invalid username or token”错误），此时先确保
#    系统安装了 git，然后自己执行：
#
#       sudo apt install git
#       git clone https://github.com/EttusResearch/pyuhd.git ~/pyuhd
#       cd ~/pyuhd
#       source ~/毕设/venv/bin/activate
#       python setup.py install
#
#    该方式不会触发 pip 的认证对话。
#
# 若你仍希望使用 pip 直接安装，可以在激活 venv 后运行：
#
#       pip install git+https://github.com/EttusResearch/pyuhd.git
#
#    但请注意有时候 pip 会要求 GitHub 凭证，这时请使用上述手动克隆方法
#    或改用 SSH URL（`git+ssh://…`）。

pip install git+https://github.com/EttusResearch/pyuhd.git

# 或者，如果你不想/不能安装 git，可以用 apt 提供的模块：
# 重新创建虚拟环境并允许系统站点包：
#    deactivate
#    python3 -m venv --system-site-packages ~/毕设/venv
#    source ~/毕设/venv/bin/activate
# 之后系统上安装的 `python3-uhd` 会自动可用。
```
如果仍然导入失败，可以手动克隆并编译：

```bash
git clone https://github.com/EttusResearch/pyuhd.git
cd pyuhd
python setup.py install
```

3. **验证安装**

```bash
# 如果你使用的是虚拟环境，请先激活：
source ~/毕设/venv/bin/activate
python -c "import uhd; print(uhd.get_version_string())"
# 或者
# python -c "import uhd; print(uhd.__version__)"
```

输出类似 `4.9.0.0` 表示绑定可用。

> ⚠️ 如果之前只是用 `sudo apt install python3-uhd` 而没有安装到虚拟环境，
> 激活 venv 后 `import uhd` 仍然会失败，这是因为标准 venv 默认不包含系统
> site-packages。要么按照上面的方法重新创建 venv，或者直接在系统 Python
>（不激活虚拟环境）下运行脚本。
```

注意：`uhd` / `gnuradio` / USRP 驱动须通过系统包（apt）或官方安装步骤完成，本仓库不包含它们。

2) CPU 推理示例（使用已有 `.pth` 模型）

> **始终在虚拟环境中运行下面的命令。** 系统 Python 被 Debian/Ubuntu
> 的包管理器托管，直接用 `sudo pip install` 会被拒绝（参见 PEP 668）。
> 如果你看到“ModuleNotFoundError: No module named 'torch'”错误，那通常只是
> 因为没有激活 venv。

在 `CCNN/gnuradio` 目录下运行：

```bash
# 每次打开新终端时先激活虚拟环境：
source ~/毕设/venv/bin/activate
cd CCNN/gnuradio
python3 realtime_infer.py --model ../2_models/best/ccnn_epoch_86_acc_0.9913.pth --num-classes 6
```

同理，所有与 GNURadio/CCNN 相关的脚本都应在 `(venv)` 提示符下执行。
“外部托管环境”错误是正常的，请不要使用 `sudo pip`。

3) 离线 npz 推理（使用训练脚本）

训练脚本位于 `CCNN/3_scripts/training/CCNN.py`，可以切换模式：

```bash
# 推理单个 npz 文件
python3 CCNN/3_scripts/training/CCNN.py --mode infer --model-path CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth --data-path CCNN/1_datasets/raw/TX_know.npz

# 在 data 文件夹上批量推理
python3 CCNN/3_scripts/training/CCNN.py --mode infer --model-path CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth --data-path CCNN/1_datasets/raw
```

4) 使用 USRP + GNURadio 工作流建议

- 使用 `gnuradio/signal_receiver.py` 进行采集与实时可视化。
  * 支持加载 CCNN 模型进行实时检测。
  * 可保存数据缓冲区到 `.npz`，例如 `--save ../1_datasets/raw/last_capture.npz`。
  * 注意：当前的实时检测需要至少 **1024 样本**的块才能送入模型，
    短数据片段将被忽略并回退至规则检测，以避免卷积层尺寸错误。
  * 如果你看到大量 `findfont` 警告，它们是 matplotlib 找不到中文字体
   （如 SimHei）导致的，对功能无影响；可以通过安装对应字体或在
    脚本内设置 `matplotlib.rcParams['font.sans-serif'] = ['Arial']` 来
    终止这些提示。
  * 运行示例：
    ```bash
    # 仅观察时域/频谱，按 Ctrl-C 退出并保存缓冲
    python3 gnuradio/signal_receiver.py --serial "serial=7MFTKFU" --save ../1_datasets/raw/last_capture.npz

    # 使用训练好的模型进行实时分类检测
    python3 gnuradio/signal_receiver.py \
        --serial "serial=7MFTKFU" \
        --model ../2_models/best/ccnn_epoch_86_acc_0.9913.pth \
        --classes 6 \
        --save ../1_datasets/raw/last_capture.npz
    ```
- 如果没有真实干扰，可用 `gnuradio/video_transmitter.py` 生成仿真信号（视频、单音或扫频）。
  - **物理回环**：将 USRP 的 TX 口通过 50Ω 同轴线连接至 RX 口，然后同时运行发送和接收脚本。
  - **软件回环**：部分 USRP 型号支持内部回环（将 `set_tx_antenna("TX/RX")` 并使用不同子设备号），可以直接在代码中配置。

  # 运行示例（已合并 TX/RX）

  ```bash
  cd ~/毕设/gnuradio
  # 直接在一个命令行里同时采集和发射单音：
  python3 signal_receiver.py \
      --serial "serial=7MFTKFU" \
      --tx-type tone --tx-freq 2.45e9 --tx-gain 15 \
      --tone-freq 1e6 \
      --save ../1_datasets/raw/last_capture.npz

  # 或者发射随机视频样本并运行 CCNN 模型检测:
  python3 signal_receiver.py \
      --serial "serial=7MFTKFU" \
      --tx-type video --tx-gain 20 \
      --model ../2_models/best/ccnn_epoch_86_acc_0.9913.pth \
      --classes 6 \
      --save ../1_datasets/raw/last_capture.npz
  ```

  # 如果仍需单独运行发送脚本
  python3 video_transmitter.py --serial "serial=7MFTKFU" --type tone --duration 60
  ```
- `realtime_infer.py` 是另一个脚本，可在接收器外调用模型每秒做一次推理。

5) 如果需要 GPU（云端）训练/加速

- 推荐在云主机上使用带 CUDA 的 PyTorch。将代码与数据上传到云，创建相同的虚拟环境并安装 CUDA 版本的 `torch`。
- 我可以帮你生成 `train.sh`、`slurm` 脚本或云端部署说明（你想用哪家云？）。

6) 下一步我可以：
-（推荐）把 `signal_receiver` 中的实时检测替换为调用 `realtime_infer.py` 的函数，实现模型推理替换规则检测。
- 或先帮你在本地（CPU）复现一次 `.npz` 文件的推理，确认模型能跑通。

告诉我你想先做哪项，我会继续操作。 
