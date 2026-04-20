%% 线性扫频（LFM）
% rs:码元速率；power:功率/dBw；fs：采样率(4×rs)；t:采样时长;
function lfm_sig = TX_LFM(rs, power, fs, T, randd)
Rs = rs;                           % 码元速率
N = fs * T;                        % 采样点数
Fs = fs;                           % 采样率
t = 0:1/Fs:(N-1)*(1/Fs);           % 时间轴
numbers = [1000, 1250, 2000, 2500];
index = randi(length(numbers));
n = ceil(N / numbers(index));                  % 扫频次数
t1 = 0:1/Fs:(N/n-1)*(1/Fs); 
power = 10.^(power/10);
p = randd;
% 改变初始频率的参数
f0 = (0.1 * rand() - 0.7)*Rs;                    % 初始干扰频率,-0.7到-0.6之间随机
K = n * (1 + 0.5 * (p/100)) * Rs/T;                                      % 斜率
y2 = [];
y2_1 = sqrt(power) * exp(1j*(2*pi*f0*t1+pi*K*t1.^2));
for i = 1:n
    y2 = [y2 y2_1];                             % 重复扫频
end
m2 = mean(abs(y2).^2);                                           
c = sqrt(power/m2);                                               
lfm_sig = c*y2;  
lfm_sig = lfm_sig(1:N);
end