%% 梳状谱（COMB）
% modulation:雷达信号调制样式(LFM\二相编码)；br:带宽(10-20MHz)；power:功率/dBw；fs：采样率；t:采样时长
function comb_sig = LD_COMB(modulation, br, power, fs, T, N, Binary_code, rand)
Fs = fs;                            % 采样频率
N0 = fs * T;                        % 采样点数
Br = br;                            % lfm信号带宽
f0 = -0.5 * Br;                     % lfm信号起始频率
N_1=ceil(N0 / 2000);                % 脉冲个数
T_PRF=T/N_1;                        % 单个脉冲时间
T_in=T_PRF/5;                       % 脉内时间
t = 0:1/Fs:T_PRF-1/Fs;
t1 = 0:1/Fs:4*T_in-1/Fs;
power = 10.^(power/10);
p = rand;
if contains(modulation, 'LFM')
    Num = 3 + randi(3);
    y2=0;
    tao1=Br/Num;
    for n = 0:Num-1
        f1 = f0 + n*tao1;
        y2 = y2+exp(1j*2*pi*f1*t1);
    end
    y2 = [y2, zeros(1, int32(T_PRF * fs - length(y2)))];
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    comb_sig = [];
        for i=1:N_1
            comb_sig=[comb_sig, y2];
        end
end
if contains(modulation, 'BPSK')
    n = N;      % 位数
    binary_code = Binary_code;
    Br=1/T_in*n;             % 信号带宽
    Num = randi([4 6]) ;
    y2=0;
    tao1=(2 + (p/100)) * (Br*6/n);
    for m = 1:Num
        f1 = -(Br*4) + m*tao1;
        y2 = y2+exp(1j*2*pi*f1*t1);
    end
    y2 = [y2, zeros(1, int32(T_PRF * fs - length(y2)))];
    m2=mean(abs(y2).^2);                                           
    c=sqrt(power/m2);                                               
    y2=c*y2;
    comb_sig = [];
        for i=1:N_1
            comb_sig=[comb_sig, y2];
        end
end
end