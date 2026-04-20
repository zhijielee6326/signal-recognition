%% 噪声乘积干扰（NP）
% modulation:雷达信号调制样式(LFM\二相编码)；br:带宽(10-20MHz)；power:功率/dBw；fs：采样率；t:采样时长
function np_sig = LD_NP(modulation, br, power, fs, T, N, Binary_code, rand)
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
d = (2 + (p/100) * 3)*10^-7;
% 高斯白噪声参数
fn=10000;                 
fs2=300 + (p/100) * 100;
fp=fs2-100;
rp=0.2;rs=10;
ws=fs2/(fn/2);
wp=fp/(fn/2);
% 产生带限高斯白噪声
u=wgn(1,N0/N_1,0);                 % 0dB高斯白噪声  
[g,Wn]=buttord(wp,ws,rp,rs);         % g：滤波器阶数，Wn：3dB截止频率
[b,b1]=butter(g,Wn);                 % 巴特沃斯低通滤波器
gt=filter(b,b1,u);                   % 高斯白噪声过低通滤波器

if contains(modulation, 'LFM')
    k=Br/T_in;
    % lfm雷达信号
    y1_delay=rectpuls(t-T_in/2-d,T_in).*exp(1j*pi*2*f0*t+1j*pi*k*t.^2);
    % 噪声乘积干扰
    y2 = y1_delay.*gt;
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    np_sig = [];
    for i=1:N_1
        np_sig=[np_sig, y2];
    end
end
if contains(modulation, 'BPSK')
    n = N; % 位数
    binary_code = Binary_code;
    len_code = length(binary_code);
    Tn = T_in / len_code;
    y1 = zeros(1, N0/N_1); % 预先分配y的长度
    f1 = -1e5 + (p/100) * 2e5;
    for ii = 1:len_code
        tmp = binary_code(ii);
        t_start = (ii-1) * Tn;
        t_end = ii * Tn;
        t_idx = find(t >= t_start & t < t_end);
        if tmp == 0
            y1(t_idx) = exp(1i * (2 * pi * f1 * t(t_idx) )); % 相位编码0对应相位0
        else
            y1(t_idx) = exp(1i * (2 * pi * f1 * t(t_idx) + pi)); % 相位编码1对应相位pi
        end
    end
    % 噪声乘积干扰
    y2 = y1.*gt;
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    np_sig = [];
    for i=1:N_1
        np_sig=[np_sig, y2];
    end
end
end