#!/usr/bin/env python3
"""
USRP模型验证测试 v4 - 精确复现MATLAB训练数据生成逻辑
完全按照TX_LFM/STJ/MTJ/NAM/NFM/SIN + PSK_MOD逐行翻译
"""

import numpy as np
from scipy import signal as sp_signal
import uhd, time, threading, queue, argparse, sys, os
sys.path.append(os.path.dirname(__file__))
from cnn_interference_detector import InterferenceDetector

# ==================== 全局参数（与MATLAB一致）====================
FS     = 2e6      # 采样率
RS     = 500e3    # 码元速率（sps=4，与MATLAB中fs=4*Rs一致）
N      = 5000     # 采样点数
T      = N / FS   # 采样时长 = 2.5ms

CENTER_FREQ = 2.45e9
TX_GAIN     = 20
RX_GAIN     = 40
BUFFER_SIZE = 4096
CCNN_PY     = "/home/zhijielee/毕设/CCNN/3_scripts/training/CCNN.py"


# ==================== MATLAB精确翻译 ====================

def _psk_power(power_dbw):
    """
    精确复现MATLAB PSK_MOD中的笔误：power = power.^(power/10)
    注意：carrier始终用0dBW，0^0=1，与10^(0/10)=1结果相同，不影响载波
    jammer用实际dBW值，用正确公式 10^(p/10)
    """
    return power_dbw ** (power_dbw / 10) if power_dbw != 0 else 1.0

def _jammer_power(power_dbw):
    """干扰信号功率：MATLAB中TX_xxx都用 power=10.^(power/10)"""
    return 10 ** (power_dbw / 10)


def _passing_filter(x, h):
    """复现MATLAB passing_filter：卷积后取中间部分"""
    half  = len(h) // 2
    y1    = np.convolve(x, h)
    return y1[half: half + len(x)]


def gen_psk(modulation='QPSK', rs=RS, power_dbw=0, fs=FS, t_dur=T):
    """
    精确复现 PSK_MOD.m
    rcosdesign(0.25, 10, sps, 'normal') + passing_filter
    """
    sps   = int(round(fs / rs))
    n_tot = int(fs * t_dur)
    n_sym = int(rs * t_dur)
    M     = {'BPSK': 2, 'QPSK': 4, '8PSK': 8}[modulation]

    data    = np.random.randint(0, M, n_sym + 20)
    angles  = 2 * np.pi * data / M
    symbols = np.exp(1j * angles)

    # upsample
    y         = np.zeros(len(symbols) * sps, dtype=complex)
    y[::sps]  = symbols

    # rcosdesign(0.25, 10, sps, 'normal') — raised cosine
    rolloff  = 0.25
    span     = 10
    ntaps    = span * sps + 1
    t_f      = np.arange(-(span * sps) // 2, (span * sps) // 2 + 1) / sps
    with np.errstate(invalid='ignore', divide='ignore'):
        numer = np.cos(np.pi * rolloff * t_f)
        denom = 1 - (2 * rolloff * t_f) ** 2
        h     = np.sinc(t_f) * numer / denom
    # 处理奇点（2*rolloff*t = ±1）
    idx = np.abs(np.abs(2 * rolloff * t_f) - 1) < 1e-6
    h[idx] = (np.pi / 4) * np.sinc(1 / (2 * rolloff))
    h[np.isnan(h)] = 0
    # MATLAB: b1 = b1/max(b1)
    h = h / np.max(np.abs(h))

    S = _passing_filter(y, h)
    S = S[:n_tot]
    if len(S) < n_tot:
        S = np.pad(S, (0, n_tot - len(S)))

    # MATLAB笔误：power = power.^(power/10)
    # carrier始终0dBW → _psk_power(0)=1，与正确公式结果相同
    power = _psk_power(power_dbw)
    m1    = np.mean(np.abs(S) ** 2)
    a     = np.sqrt(power / (m1 + 1e-12))
    return (a * S).astype(np.complex64)


def gen_lfm(rs=RS, power_dbw=10, fs=FS, t_dur=T, randd=None):
    """精确复现 TX_LFM.m"""
    if randd is None:
        randd = np.random.randint(1, 101)
    N_  = int(fs * t_dur)
    Fs  = fs
    numbers = [1000, 1250, 2000, 2500]
    index   = np.random.randint(0, len(numbers))
    n       = int(np.ceil(N_ / numbers[index]))      # 扫频次数

    n_per = N_ // n                                   # 每次扫频点数
    t1    = np.arange(n_per) / Fs
    power = _jammer_power(power_dbw)
    p     = randd

    f0 = (0.1 * np.random.rand() - 0.7) * rs        # -0.7rs ~ -0.6rs
    K  = n * (1 + 0.5 * (p / 100)) * rs / t_dur

    y2_1 = np.sqrt(power) * np.exp(1j * (2*np.pi*f0*t1 + np.pi*K*t1**2))
    y2   = np.tile(y2_1, n + 1)[:N_]                 # 多tile一次再截取，确保够N_个

    m2  = np.mean(np.abs(y2) ** 2)
    c   = np.sqrt(power / (m2 + 1e-12))
    return (c * y2).astype(np.complex64)


def gen_stj(rs=RS, power_dbw=10, fs=FS, t_dur=T, randd=None):
    """精确复现 TX_STJ.m"""
    if randd is None:
        randd = np.random.randint(1, 101)
    N_ = int(fs * t_dur)
    t  = np.arange(N_) / fs
    p  = randd
    power = _jammer_power(power_dbw)

    up = 0.01 * rs * 1.2
    f0 = -0.6 * rs + up * p             # 范围：-0.6rs ~ +0.6rs

    y2 = np.sqrt(power) * np.exp(1j * 2 * np.pi * f0 * t)
    m2 = np.mean(np.abs(y2) ** 2)
    c  = np.sqrt(power / (m2 + 1e-12))
    return (c * y2).astype(np.complex64)


def gen_mtj(rs=RS, power_dbw=10, fs=FS, t_dur=T):
    """精确复现 TX_MTJ.m"""
    N_ = int(fs * t_dur)
    t  = np.arange(N_) / fs
    n  = 2 + np.random.randint(1, 6)    # randi(5)+2 → 3~6
    power = _jammer_power(power_dbw)

    totalRange = 1.6 * rs
    Length     = totalRange / 16
    # randperm(16,8) → 从16个中选8个不重复（1-indexed）
    ra = np.random.choice(16, 8, replace=False) + 1

    z = np.zeros(n)
    for p_idx in range(n):
        start    = -0.8 * rs + (ra[p_idx] - 1) * Length
        z[p_idx] = start + Length / 2

    y2 = np.zeros(N_, dtype=complex)
    for q in range(n):
        y2 += np.exp(1j * 2 * np.pi * z[q] * t)    # A0=1

    m2 = np.mean(np.abs(y2) ** 2)
    c  = np.sqrt(power / (m2 + 1e-12))
    return (c * y2).astype(np.complex64)


def gen_nam(rs=RS, power_dbw=10, fs=FS, t_dur=T, randd=None):
    """精确复现 TX_NAM.m"""
    if randd is None:
        randd = np.random.randint(1, 101)
    N_ = int(fs * t_dur)
    t  = np.arange(N_) / fs
    p  = randd
    power = _jammer_power(power_dbw)

    fn  = 10000.0
    fs1 = 800 + (p / 100) * 400          # 截止频率
    fp  = fs1 - 100
    ws  = fs1 / (fn / 2)
    wp  = fp  / (fn / 2)

    order, wn = sp_signal.buttord(wp, ws, 0.2, 3)
    b, a_c    = sp_signal.butter(order, wn, btype='low')

    # wgn(1,N,0) → 0dBW高斯白噪声，功率=1
    u  = np.random.randn(N_)
    x0 = sp_signal.lfilter(b, a_c, u)

    A   = 1.0
    Kam = 2 + (p / 100) * 8
    f0  = np.random.randint(int(-0.1 * rs), int(0.1 * rs) + 1)
    theta = 2 * np.pi * np.random.rand()

    y2 = (A + Kam * x0) * np.exp(1j * (2 * np.pi * f0 * t + theta))
    m2 = np.mean(np.abs(y2) ** 2)
    c  = np.sqrt(power / (m2 + 1e-12))
    return (c * y2).astype(np.complex64)


def gen_nfm(rs=RS, power_dbw=10, fs=FS, t_dur=T, randd=None):
    """精确复现 TX_NFM.m"""
    if randd is None:
        randd = np.random.randint(1, 101)
    N_ = int(fs * t_dur)
    t  = np.arange(N_) / fs
    p  = randd
    power = _jammer_power(power_dbw)

    fn  = 10000.0
    fs1 = 150 + (p / 100) * 50
    fp  = fs1 - 100
    ws  = fs1 / (fn / 2)
    wp  = fp  / (fn / 2)

    order, wn = sp_signal.buttord(wp, ws, 0.2, 3)
    b, a_c    = sp_signal.butter(order, wn, btype='low')

    # wgn(1,N,-10) → -10dBW，功率=0.1
    u  = np.sqrt(10 ** (-10 / 10)) * np.random.randn(N_)
    x0 = sp_signal.lfilter(b, a_c, u)

    # MATLAB定义法积分：sum(i+1)=x0(i)+sum(i)，sum(1)=0
    xn = np.zeros(N_)
    for i in range(N_ - 1):
        xn[i + 1] = x0[i] + xn[i]

    Kfm   = 0.3 + (p / 100) * 0.4
    f0    = np.random.randint(int(-0.1 * rs), int(0.1 * rs) + 1)
    theta = 2 * np.pi * np.random.rand()
    A     = np.sqrt(power)

    y2 = A * np.exp(1j * (2 * np.pi * f0 * t + 2 * np.pi * Kfm * xn + theta))
    m2 = np.mean(np.abs(y2) ** 2)
    c  = np.sqrt(power / (m2 + 1e-12))
    return (c * y2).astype(np.complex64)


def gen_sin_jammer(rs=RS, power_dbw=10, fs=FS, t_dur=T, randd=None):
    """精确复现 TX_SIN.m"""
    if randd is None:
        randd = np.random.randint(1, 101)
    N_ = int(fs * t_dur)
    t  = np.arange(N_) / fs
    p  = randd
    power = _jammer_power(power_dbw)

    f  = 5e4 + (p / 100) * 5e4           # 50kHz~100kHz
    fc = np.random.randint(int(-0.1 * rs), int(0.1 * rs) + 1)

    sin_data = np.sin(f * t)
    # MATLAB定义法积分
    xn = np.zeros(N_)
    for i in range(N_ - 1):
        xn[i + 1] = sin_data[i] + xn[i]

    y2 = np.exp(1j * (fc * t + (0.6 + 0.4 * (p / 100)) * xn))
    m2 = np.mean(np.abs(y2) ** 2)
    c  = np.sqrt(power / (m2 + 1e-12))
    return (c * y2).astype(np.complex64)


# ==================== 叠加信号（载波+干扰）====================

GEN_MAP = {
    'lfm': gen_lfm,
    'mtj': lambda rs, pwr, fs, t: gen_mtj(rs, pwr, fs, t),
    'nam': gen_nam,
    'nfm': gen_nfm,
    'stj': gen_stj,
    'sin': gen_sin_jammer,
}

TYPE_LABEL = {
    'lfm': "扫频干扰(LFM)",
    'mtj': "多音干扰(MTJ)",
    'nam': "窄带AM(NAM)",
    'nfm': "窄带FM(NFM)",
    'stj': "单音干扰(STJ)",
    'sin': "正弦波(SIN)",
    'clean': "无干扰",
}


def make_combined(jammer_type, jsr_db=10,
                  modulation=None, rs=RS, fs=FS, t_dur=T):
    """
    生成 载波(0dBW) + 干扰(jsr_db dBW) 叠加信号
    与训练数据格式完全一致
    """
    if modulation is None:
        modulation = np.random.choice(['QPSK', '8PSK', 'BPSK'])

    randd   = np.random.randint(1, 101)
    carrier = gen_psk(modulation, rs, 0, fs, t_dur)

    gen_fn  = GEN_MAP[jammer_type]
    # MTJ没有randd参数
    if jammer_type == 'mtj':
        jammer = gen_fn(rs, jsr_db, fs, t_dur)
    else:
        jammer = gen_fn(rs, jsr_db, fs, t_dur, randd)

    return (carrier + jammer).astype(np.complex64)


# ==================== USRP收发器 ====================

class USRPTransceiver:
    def __init__(self, serial):
        self.usrp = uhd.usrp.MultiUSRP(serial)
        self.usrp.set_tx_rate(FS, 0)
        self.usrp.set_tx_freq(uhd.libpyuhd.types.tune_request(CENTER_FREQ), 0)
        self.usrp.set_tx_gain(TX_GAIN, 0)
        self.usrp.set_tx_antenna("TX/RX", 0)
        self.tx_stream = self.usrp.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))

        self.usrp.set_rx_rate(FS, 0)
        self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(CENTER_FREQ), 0)
        self.usrp.set_rx_gain(RX_GAIN, 0)
        self.usrp.set_rx_antenna("RX2", 0)
        sa      = uhd.usrp.StreamArgs("fc32", "sc16")
        sa.args = "recv_frame_size=4096,num_recv_frames=512"
        self.rx_stream  = self.usrp.get_rx_stream(sa)

        self.rx_queue   = queue.Queue(maxsize=100)
        self.tx_queue   = queue.Queue(maxsize=50)
        self.is_running = False
        print(f"✓ USRP @ {CENTER_FREQ/1e9:.2f}GHz  "
              f"FS={FS/1e6:.0f}MHz  TX={TX_GAIN}dB  RX={RX_GAIN}dB")

    def _tx_worker(self):
        while self.is_running:
            try:
                sig  = self.tx_queue.get(timeout=0.5)
                meta = uhd.types.TXMetadata()
                meta.start_of_burst = True
                meta.end_of_burst   = True
                self.tx_stream.send(sig.reshape(1, -1), meta)
            except queue.Empty:
                continue

    def _rx_worker(self):
        cmd            = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        cmd.stream_now = True
        self.rx_stream.issue_stream_cmd(cmd)
        buf  = np.zeros((1, BUFFER_SIZE), dtype=np.complex64)
        meta = uhd.types.RXMetadata()
        while self.is_running:
            try:
                n = self.rx_stream.recv(buf, meta)
                if n > 0:
                    try:
                        self.rx_queue.put(buf[0][:n].copy(), block=False)
                    except queue.Full:
                        try:
                            self.rx_queue.get_nowait()
                            self.rx_queue.put(buf[0][:n].copy(), block=False)
                        except Exception:
                            pass
            except Exception:
                pass

    def start(self):
        self.is_running = True
        threading.Thread(target=self._tx_worker, daemon=True).start()
        threading.Thread(target=self._rx_worker, daemon=True).start()
        print("✓ 收发线程已启动")

    def stop(self):
        self.is_running = False
        time.sleep(0.3)
        self.rx_stream.issue_stream_cmd(
            uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont))
        print("✓ 收发已停止")

    def send(self, sig):
        try:
            self.tx_queue.put(sig, block=False)
        except queue.Full:
            pass

    def recv_n(self, n_samples, timeout=2.0):
        buf   = []
        t_end = time.time() + timeout
        while len(buf) < n_samples and time.time() < t_end:
            try:
                chunk = self.rx_queue.get(timeout=0.2)
                buf.extend(chunk)
            except queue.Empty:
                pass
        if len(buf) >= n_samples:
            return np.array(buf[:n_samples], dtype=np.complex64)
        return None


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(description="USRP模型验证（精确复现MATLAB信号）")
    parser.add_argument('--serial',  default="serial=7MFTKFU")
    parser.add_argument('--model',
        default="/home/zhijielee/毕设/CCNN/2_models/best/ccnn_epoch_86_acc_0.9913.pth")
    parser.add_argument('--classes', type=int,   default=6)
    parser.add_argument('--tests',   type=int,   default=10)
    parser.add_argument('--jsr',     type=float, default=10,
        help='干信比dB（训练集用6或10）')
    parser.add_argument('--type',    default='all',
        choices=list(TYPE_LABEL.keys()) + ['all'])
    args = parser.parse_args()

    detector   = InterferenceDetector(args.model, CCNN_PY, args.classes)
    trx        = USRPTransceiver(args.serial)
    test_types = list(TYPE_LABEL.keys()) if args.type == 'all' else [args.type]
    results    = {t: {'correct': 0, 'total': 0} for t in test_types}

    print(f"\n{'='*65}")
    print(f"USRP实机验证  RS={RS/1e3:.0f}kHz  JSR={args.jsr}dB")
    print(f"{'='*65}")

    trx.start()
    time.sleep(1)

    for ttype in test_types:
        expected = TYPE_LABEL[ttype]
        print(f"\n测试 [{ttype.upper()}] → 期望: {expected}")

        for i in range(args.tests):
            sig = make_combined(ttype, jsr_db=args.jsr)
            trx.send(sig)
            time.sleep(0.15)

            rx = trx.recv_n(N, timeout=1.5)
            if rx is not None:
                det, conf = detector.detect(rx)
                ok        = (det == expected)
                results[ttype]['total']   += 1
                results[ttype]['correct'] += ok
                print(f"  [{i+1:2d}/{args.tests}] {'✓' if ok else '✗'} "
                      f"检测: {det} ({conf:.2f})")
            else:
                print(f"  [{i+1:2d}/{args.tests}] ⚠️  数据不足")
            time.sleep(0.2)

    trx.stop()

    print(f"\n{'='*65}")
    total_c = total_t = 0
    for ttype in test_types:
        r = results[ttype]
        if r['total'] == 0:
            continue
        acc = r['correct'] / r['total'] * 100
        bar = '█' * int(acc / 5) + '░' * (20 - int(acc / 5))
        print(f"  {ttype.upper():>5}  {bar}  {r['correct']}/{r['total']} = {acc:.0f}%")
        total_c += r['correct']
        total_t += r['total']
    if total_t:
        oa = total_c / total_t
        print(f"\n  总体准确率: {oa:.1%}  ({total_c}/{total_t})")
        if oa < 0.5:
            print(f"\n⚠️  准确率偏低，请尝试调整JSR：")
            print(f"   python3 {os.path.basename(__file__)} --jsr 6")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
