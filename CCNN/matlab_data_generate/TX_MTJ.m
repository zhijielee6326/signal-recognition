%% 多音干扰（MTJ）
% rs:码元速率；power:功率/dBw；fs：采样率；t:采样时长
function mtj_sig = TX_MTJ(rs, power, fs, T)
Rs = rs;                          % 码元速率
N = fs * T;                        % 采样点数
Fs = fs;                           % 采样率
t = 0:1/Fs:(N-1)*(1/Fs);           % 时间轴
n = 2 + randi(5);
power = 10.^(power/10);
totalRange = 1.6 * Rs;                             % 总范围从-0.8Rb到0.8Rb
Length = totalRange / 16;                          % 每个间隔的长度
ra = randperm(16, 8);                              % 从16个间隔中随机选择8个
z = zeros(1, n);                                   % 初始化一个数组
for p = 1:n
    start = -0.8 * Rs + (ra(p) - 1) * Length;      % 计算间隔的开始
    z(p) = start + Length / 2;                     % 计算区间的中点
end
y2 = 0;
A0 = 1;
for q = 0:n-1
    y2 = y2+A0*exp(1i*2*pi*z(q+1)*t);
end
m2 = mean(abs(y2).^2);
c = sqrt(power/m2);                                               
mtj_sig = c*y2; 
end