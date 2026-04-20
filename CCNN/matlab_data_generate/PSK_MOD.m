%% 通信信号
% modulation:调制样式(BPSK\QPSK\8PSK)；rs:码元速率；power:功率/dBw；fs：采样率；t:采样时长
function psk_sig = PSK_MOD(modulation, rs, power, fs, T)
Rs = rs;                          % 码元速率
sps = fs / Rs;                     % 单个符号采样点数
N = fs * T;                        % 采样点数
n = Rs * T;                        % 符号数
% PSK
if contains(modulation, 'BPSK')
    M = 2;
    data = randi([0 M-1],1,n);     % 随机符号数据
    moddata = pskmod(data,M);      % 基带信号
    y = upsample(moddata,sps);     % 上采样
    % shape filter
    b1 = rcosdesign(0.25,10,sps,'normal'); 
    b1 = b1/max(b1);
    S = passing_filter(y,b1);
end
if contains(modulation, 'QPSK')
    M = 4;
    data = randi([0 M-1],1,n);
    moddata = pskmod(data,M);
    y = upsample(moddata,sps);
    % shape filter
    b1 = rcosdesign(0.25,10,sps,'normal'); 
    b1 = b1/max(b1);
    S = passing_filter(y,b1);
end
if contains(modulation, '8PSK')
    M = 8;
    data = randi([0 M-1],1,n);
    moddata = pskmod(data,M);
    y = upsample(moddata,sps);
    % shape filter
    b1 = rcosdesign(0.25,10,sps,'normal'); 
    b1 = b1/max(b1);
    S = passing_filter(y,b1);
end

% 功率控制
m1 = mean(abs(S).^2);   
power = power.^(power/10);
a = sqrt(power/m1);                                               
psk_sig = a*S;

function y=passing_filter(x,h)              
len=floor(length(h)/2);
y1=conv(x,h);
y=y1(len+1:len+length(x));
end
end