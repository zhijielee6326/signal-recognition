#!/usr/bin/env python3
"""
USRP实机JSR扫描 - 连续发送版
参照complete_system.py：TX连续循环发送，RX持续接收，两者并行
"""
import numpy as np, uhd, time, threading, queue
import sys, os, glob, json
sys.path.append('/home/zhijielee/毕设/gnuradio')
from cnn_interference_detector import InterferenceDetector

FS          = 2e6
CENTER_FREQ = 1e9
RX_GAIN     = 70
N           = 5000
TRAIN_DIR   = os.path.expanduser("~/毕设/CCNN/1_datasets/train")
CCNN_PY     = "/home/zhijielee/毕设/CCNN/3_scripts/training/CCNN.py"
MODEL_PTH = "/home/zhijielee/毕设/CCNN/2_models/legacy/TXCCNNmodel1013.pth"

TYPE_LABEL = {
    'lfm': "扫频干扰(LFM)", 'mtj': "多音干扰(MTJ)",
    'nam': "窄带AM(NAM)",   'nfm': "窄带FM(NFM)",
    'stj': "单音干扰(STJ)", 
}

class USRP:
    def __init__(self, serial="serial=7MFTKFU"):
        # TX
        self.tx_dev = uhd.usrp.MultiUSRP(serial)
        self.tx_dev.set_tx_rate(FS, 0)
        self.tx_dev.set_tx_freq(uhd.libpyuhd.types.tune_request(CENTER_FREQ), 0)
        self.tx_dev.set_tx_gain(25, 0)
        self.tx_dev.set_tx_antenna("TX/RX", 0)
        self.tx_st = self.tx_dev.get_tx_stream(
            uhd.usrp.StreamArgs("fc32", "sc16"))
        # RX
        self.rx_dev = uhd.usrp.MultiUSRP(serial)
        self.rx_dev.set_rx_rate(FS, 0)
        self.rx_dev.set_rx_freq(uhd.libpyuhd.types.tune_request(CENTER_FREQ), 0)
        self.rx_dev.set_rx_gain(RX_GAIN, 0)
        self.rx_dev.set_rx_antenna("RX2", 0)
        sa = uhd.usrp.StreamArgs("fc32", "sc16")
        sa.args = "recv_frame_size=4096,num_recv_frames=512"
        self.rx_st = self.rx_dev.get_rx_stream(sa)

        self.rxq        = queue.Queue(maxsize=500)
        self.tx_sig     = None   # 当前发送的信号
        self.tx_running = False
        self.rx_running = False
        print(f"✓ USRP就绪  {CENTER_FREQ/1e9:.1f}GHz  FS={FS/1e6:.0f}MHz")

    def set_tx_gain(self, gain):
        self.tx_dev.set_tx_gain(gain, 0)
        time.sleep(0.1)

    def set_tx_signal(self, sig):
        """切换发送信号（线程安全）"""
        self.tx_sig = sig

    def _tx_worker(self):
        """持续循环发送当前信号"""
        meta = uhd.types.TXMetadata()
        meta.start_of_burst = True
        meta.end_of_burst   = True
        while self.tx_running:
            sig = self.tx_sig
            if sig is not None:
                self.tx_st.send(sig.reshape(1, -1), meta)
            else:
                time.sleep(0.001)

    def _rx_worker(self):
        cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        cmd.stream_now = True
        self.rx_st.issue_stream_cmd(cmd)
        buf  = np.zeros((1, 4096), dtype=np.complex64)
        meta = uhd.types.RXMetadata()
        while self.rx_running:
            try:
                n = self.rx_st.recv(buf, meta)
                if n > 0:
                    try:
                        self.rxq.put(buf[0][:n].copy(), block=False)
                    except queue.Full:
                        try:
                            self.rxq.get_nowait()
                            self.rxq.put(buf[0][:n].copy(), block=False)
                        except Exception:
                            pass
            except Exception:
                pass

    def start(self):
        self.tx_running = True
        self.rx_running = True
        threading.Thread(target=self._tx_worker, daemon=True).start()
        threading.Thread(target=self._rx_worker, daemon=True).start()
        time.sleep(0.5)
        print("✓ TX/RX线程已启动")

    def stop(self):
        self.tx_running = False
        self.rx_running = False
        time.sleep(0.2)
        self.rx_st.issue_stream_cmd(
            uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont))

    def flush(self):
        while True:
            try: self.rxq.get_nowait()
            except queue.Empty: break
        time.sleep(0.1)
        while True:
            try: self.rxq.get_nowait()
            except queue.Empty: break

    def collect(self, n_samples, timeout=1.0):
        buf = []
        end = time.time() + timeout
        while len(buf) < n_samples and time.time() < end:
            try:
                chunk = self.rxq.get(timeout=0.05)
                buf.extend(chunk)
            except queue.Empty:
                pass
        if len(buf) >= n_samples:
            return np.array(buf[:n_samples], dtype=np.complex64)
        return None


def load_samples():
    samples = {}
    key_map = {'LFM':'lfm','MTJ':'mtj','NAM':'nam',
               'NFM':'nfm','STJ':'stj'}
    for fpath in sorted(glob.glob(os.path.join(TRAIN_DIR, '*.npz'))):
        fname = os.path.basename(fpath)
        for tname, key in key_map.items():
            if f'_{tname}_' in fname or f'_{tname}.' in fname:
                try:
                    f = np.load(fpath, mmap_mode='r')
                    if 'data' in f.files:
                        if key not in samples: samples[key] = []
                        samples[key].append(f['data'])
                except Exception:
                    pass
                break
    merged = {k: np.concatenate(v, axis=0) for k,v in samples.items()}
    print("样本数:", {k: len(v) for k,v in merged.items()})
    return merged

def make_tx(samples, ttype, jsr_db):
    arr = samples.get(ttype)
    if arr is None: return None
    iq  = arr[np.random.randint(len(arr))]
    sig = (iq[0]+1j*iq[1]).astype(np.complex64)
    sig /= (np.sqrt(np.mean(np.abs(sig)**2))+1e-8)
    noise = (np.random.randn(N)+1j*np.random.randn(N)).astype(np.complex64)
    noise *= np.sqrt(0.5/(10**(jsr_db/10)))
    return sig + noise


# ==================== 主程序 ====================
usrp = USRP()

# 加载测试样本
test_sig = None
for fpath in glob.glob(os.path.join(TRAIN_DIR, '*_STJ_*.npz')):
    f = np.load(fpath)
    iq = f['data'][0]
    test_sig = (iq[0]+1j*iq[1]).astype(np.complex64)
    test_sig /= np.sqrt(np.mean(np.abs(test_sig)**2))
    print(f"测试样本: {os.path.basename(fpath)}")
    break

usrp.set_tx_signal(test_sig)   # 设置发送信号
usrp.start()                    # TX/RX同时启动

# ==================== 第一步：扫增益 ====================
print(f"\n{'='*60}")
print("第一步：扫TX增益（连续发送模式）")
print(f"{'TX增益':>8}  {'RX功率':>12}  {'TX/RX比':>9}  {'MaxAmp':>8}  状态")
print(f"{'='*60}")

best_gain  = 25
best_ratio = 999

for tx_gain in [10, 15, 20, 25, 30, 40]:
    usrp.set_tx_gain(tx_gain)
    usrp.flush()
    time.sleep(0.2)             # 等连续信号稳定
    rx = usrp.collect(N, 0.5)  # 从连续流中取一帧

    if rx is None:
        print(f"{tx_gain:>7}dB  收数据失败")
        continue

    rx_pwr  = np.mean(np.abs(rx)**2)
    max_amp = np.max(np.abs(rx))
    ratio   = 10*np.log10(1.0/(rx_pwr+1e-12))

    if max_amp > 0.85:   status = "⚠️  RX饱和"
    elif ratio < 5:      status = "✓✓ 信号强"
    elif ratio < 15:     status = "✓  信号良好"
    elif ratio < 30:     status = "△  信号弱"
    else:                status = "✗  噪声"

    print(f"{tx_gain:>7}dB  {rx_pwr:>12.6f}  {ratio:>8.1f}dB  "
          f"{max_amp:>8.4f}  {status}")

    if ratio < best_ratio and max_amp < 0.85:
        best_ratio = ratio
        best_gain  = tx_gain

print(f"\n使用TX增益: {best_gain}dB  (TX/RX比: {best_ratio:.1f}dB)")

if best_ratio > 35:
    print("⚠️  信号仍然很弱，继续用最大增益跑测试")
    best_gain = 40
    usrp.set_tx_gain(best_gain)

# ==================== 第二步：JSR扫描 ====================
print(f"\n{'='*60}")
print(f"第二步：JSR扫描  TX={best_gain}dB  连续发送  CCNN模型")
print(f"{'='*60}")

print("加载数据和模型...")
samples  = load_samples()
detector = InterferenceDetector(MODEL_PTH, CCNN_PY, 5)
usrp.set_tx_gain(best_gain)

JSR_LIST   = [-4, 0, 4, 6, 8, 10, 12, 14, 16]
N_TRIALS   = 20
test_types = [t for t in TYPE_LABEL if samples.get(t) is not None]
results    = {t: [] for t in test_types}

print(f"\n{'JSR':>5}", end='')
for t in test_types:
    print(f"  {t.upper():>6}", end='')
print()

try:
    for jsr in JSR_LIST:
        print(f"{jsr:>5}", end='', flush=True)
        for ttype in test_types:
            correct = total = 0

            # 切换信号，等稳定后再收
            sig_template = make_tx(samples, ttype, jsr)
            usrp.set_tx_signal(sig_template)
            usrp.flush()
            time.sleep(0.15)   # 等连续信号建立

            for _ in range(N_TRIALS):
                # 每次取新样本（带随机噪声）
                sig = make_tx(samples, ttype, jsr)
                usrp.set_tx_signal(sig)
                time.sleep(0.05)
                rx = usrp.collect(N, timeout=0.3)
                if rx is not None:
                    det, _ = detector.detect(rx)
                    correct += (det == TYPE_LABEL[ttype])
                    total   += 1
                time.sleep(0.01)

            acc = correct/max(total,1)*100
            results[ttype].append(round(acc,1))
            print(f"  {acc:>5.1f}%", end='', flush=True)
        print()

except KeyboardInterrupt:
    print("\n用户中断")
finally:
    usrp.stop()

out_data = {'jsr':JSR_LIST,'types':test_types,'results':results,
            'config':{'tx_gain':best_gain,'rx_gain':RX_GAIN,
                      'n_trials':N_TRIALS,'freq':CENTER_FREQ,'fs':FS}}
with open('usrp_jsr_results.json','w') as f:
    json.dump(out_data, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"{'':>6}", end='')
for jsr in JSR_LIST:
    print(f"  {int(jsr):>3}dB", end='')
print()
for ttype in test_types:
    print(f"{ttype.upper():>6}", end='')
    for acc in results[ttype]:
        print(f"  {acc:>4.0f}%", end='')
    print()
print(f"\n✓ 已保存 usrp_jsr_results.json")
print(f"  python3 plot_usrp_jsr.py  生成图表")
