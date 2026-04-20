%% 单音干扰（STJ）
% rs:码元速率；power:功率/dBw；fs：采样率；t:采样时长
function stj_sig = TX_STJ(rs, power, fs, T, randd)
Rs = rs;                          % 码元速率
N = fs * T;                        % 采样点数
Fs = fs;                           % 采样率
t = 0:1/Fs:(N-1)*(1/Fs);           % 时间轴
p = randd;
up = 0.01 * Rs * 1.2;
f0= -0.6*Rs + up*p;                   % 干扰频率
% f0 = f0*10^-6;                     % 单位为Mhz
power = 10.^(power/10);
y2 = sqrt(power)*exp(1i*2*pi*f0*t);
m2 = mean(abs(y2).^2);                                           
c = sqrt(power/m2);                                               
stj_sig = c*y2; 
end
