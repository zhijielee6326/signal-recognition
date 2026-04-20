%% 雷达信号
% modulation:调制样式(LFM\二相编码)；br:带宽(10-20MHz)；power:功率/dBm；fs：采样率；t:采样时长
function LD_sig = LD_MOD(modulation, br, power, fs, T, N, Binary_code, rand)
Fs = fs;                            % 采样频率
N0 = fs * T;                        % 采样点数
Br = br;                            % lfm信号带宽
f0 = -0.5 * Br;                     % lfm信号起始频率
N_1=ceil(N0 / 2000);                % 脉冲个数
T_PRF=T/N_1;                        % 单个脉冲时间
T_in=T_PRF/5;                       % 脉内时间
t = 0:1/Fs:T_PRF-1/Fs;
power = 10.^(power/10);
p = rand;
if contains(modulation, 'LFM')      
    k=Br/T_in;
    %%lfm雷达信号
    y1=rectpuls(t-T_in/2,T_in).*exp(1j*pi*2*f0*t+1j*pi*k*t.^2);
    m1=mean(abs(y1).^2);                                           
    a=sqrt(power/m1);                                               
    y1 = a*y1;
    LD_sig = [];
    for i = 1:N_1
        LD_sig = [LD_sig, y1];
    end
end
if contains(modulation, 'BPSK')
    n = N; % 位数
    binary_code = Binary_code;
    len_code = length(binary_code);
    Tn = T_in / len_code;
    y0 = zeros(1, N0/N_1); % 预先分配y的长度
    for ii = 1:len_code
        tmp = binary_code(ii);
        t_start = (ii-1) * Tn;
        t_end = ii * Tn;
        t_idx = find(t >= t_start & t < t_end);
        f1 = -1e5 + (p/100) * 2e5;
        if tmp == 0
            y0(t_idx) = exp(1i * (2 * pi * f1 * t(t_idx) )); % 相位编码0对应相位0
        else
            y0(t_idx) = exp(1i * (2 * pi * f1 * t(t_idx) + pi)); % 相位编码1对应相位pi
        end
    end
    m1 = mean(abs(y0).^2);                                           
    a = sqrt(power/m1);                                               
    y1 = a*y0;
    LD_sig = [];
    for i = 1:N_1
        LD_sig = [LD_sig, y1];
    end
end
end