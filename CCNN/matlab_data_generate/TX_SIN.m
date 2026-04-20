%% 正弦调频（SIN）
% rs:码元速率；power:功率/dBw；fs：采样率；t:采样时长
function sin_sig = TX_SIN(rs, power, fs, T, randd)
Rs = rs;                          % 码元速率
N = fs * T;                        % 采样点数
Fs = fs;                           % 采样率
t = 0:1/Fs:(N-1)*(1/Fs);           % 时间轴
power = 10.^(power/10);
p = randd;
% sin干扰
f = 5e4 + (p/100) * 5e4;          % 干扰参数
fc = randi([-0.1*Rs 0.1*Rs]);   % 干扰中心频率
sin_data = sin(f*t);            % 干扰波形
sum(1) = 0;                     % 定义法求积分
for i = 1:N-1             
    sum(i+1) = sin_data(i) + sum(i);
end
y2 = exp(1j*(fc*t + (0.6 + 0.4 * (p/100)) * sum));
m2 = mean(abs(y2).^2);                                           
c = sqrt(power/m2);                                               
sin_sig = c*y2; 
end