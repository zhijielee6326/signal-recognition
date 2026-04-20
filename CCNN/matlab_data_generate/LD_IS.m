%% 间接采样转发（IS）
% modulation:雷达信号调制样式(LFM\二相编码)；br:带宽(10-20MHz)；power:功率/dBw；fs：采样率；t:采样时长
function is_sig = LD_IS(modulation, br, power, fs, T, N, Binary_code, rand)
Fs = fs;                            % 采样频率
N0 = fs * T;                        % 采样点数
Br = br;                            % lfm信号带宽
f0 = -0.5 * Br;                     % lfm信号起始频率
N_1=ceil(N0 / 2000);                % 脉冲个数
T_PRF=T/N_1;                        % 单个脉冲时间
T_in=T_PRF/5;                       % 脉内时间
t = 0:1/Fs:T_PRF-1/Fs;
t1 = 0:1/Fs:T_in-1/Fs;
power = 10.^(power/10);
p = rand;
d = (5 + (p/100) * 9)*10^-7;
Num = 2 + randi(3);
Tc=T_in/Num/2;                        %单个采样重复周期内采样信号长度
if contains(modulation, 'LFM')
    k=Br/T_in;
    y2=0;
    for n = 0:Num-1
        y2 = y2 + rectpuls((t-d-(2*n+1).*Tc-Tc/2),Tc).*exp(1j*pi*2*f0*(t-d)+1j*pi*k*(t-d).^2);
    end
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    is_sig = [];
        for i=1:N_1
            is_sig=[is_sig, y2];
        end
end
if contains(modulation, 'BPSK')
    n = N; % 位数
    binary_code = Binary_code;
    len_code = length(binary_code);
    Tn = T_in / len_code;
    y0 = zeros(1, int32(Fs*T_PRF)); % 预先分配y的长度
    f1 = -1e5 + (p/100) * 2e5;
    for ii = 1:len_code
        tmp = binary_code(ii);
        t_start = (ii-1) * Tn;
        t_end = ii * Tn;
        t_idx = find(t >= t_start & t < t_end);
        if tmp == 0
            y0(t_idx) = exp(1i * (2 * pi * f1 * t(t_idx) )); % 相位编码0对应相位0
        else
            y0(t_idx) = exp(1i * (2 * pi * f1 * t(t_idx) + pi)); % 相位编码1对应相位pi
        end
    end
    % 间接采样转发
    % y0 是 y1 的延时版本
    y_delay = zeros(1, length(t));
    d_idx = round(d * Fs);
    y_delay(d_idx+1:end) = y0(1:end-d_idx);
    y2 = zeros(1, length(t)); % 预先分配y2的长度
    for n_bp = 0:Num-1
        p_t = rectpuls((t - d -(2*n_bp+1)*Tc-Tc/2), Tc);
        y2 = y2 + p_t .* y_delay;
    end  
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    is_sig = [];
        for i=1:N_1
            is_sig=[is_sig, y2];
        end
end