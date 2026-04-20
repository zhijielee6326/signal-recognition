%% 全脉冲密集转发（WDTJ）
% modulation:雷达信号调制样式(LFM\二相编码)；br:带宽(10-20MHz)；power:功率/dBw；fs：采样率；t:采样时长
function wdtj_sig = LD_WDTJ(modulation, br, power, fs, T, N, Binary_code, rand)
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
d = (5 + 5.*rand())*10^-8;
Num = 2 + randi(3);
tao1=(15 + (p/100) * 3)*5e-7;       %密集转发时延
if contains(modulation, 'LFM')
    k=Br/T_in;
    y2=0;
    for n = 1:Num
        tao = d+(n-1)*tao1;
        y2 = y2 + rectpuls(t-T_in/2-tao,T_in).*exp(1j*pi*2*f0*(t-tao)+1j*pi*k*(t-tao).^2);
    end
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    wdtj_sig = [];
        for i=1:N_1
            wdtj_sig=[wdtj_sig, y2];
        end
end
if contains(modulation, 'BPSK')
    n = N; % 位数
    binary_code = Binary_code;
    len_code = length(binary_code);
    Tn = T_in / len_code;
    y0 = zeros(1, N0/N_1); % 预先分配y的长度
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
    % 全脉冲
    y2 = zeros(1, length(t)); % 预先分配y2的长度
    for n = 1:Num
        tao = d + (n-1) * tao1;
        % 延时后的二相编码信号
        y_delayed = zeros(1, length(t));
        tao_idx = round(tao * Fs);
        if tao_idx < length(t)
            y_delayed(tao_idx+1:end) = y0(1:end-tao_idx);
        end
        y2 = y2 + rectpuls(t - T_in/2 - tao, T_in) .* y_delayed;
    end        
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    wdtj_sig = [];
        for i=1:N_1
            wdtj_sig = [wdtj_sig, y2];
        end
end
end
