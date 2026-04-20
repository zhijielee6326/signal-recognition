%% 噪声调幅（NAM）
% rs:码元速率；power:功率/dBw；fs：采样率；t:采样时长
function nam_sig = TX_NAM(rs, power, fs, T, randd)
Rs = rs;                           % 码元速率
N = fs * T;                        % 采样点数
Fs = fs;                           % 采样率
t = 0:1/Fs:(N-1)*(1/Fs);           % 时间轴
power = 10.^(power/10);
p = randd;
% 滤波器系数
fn = 10000;                 % 采样频率
fs1 = 800 + (p/100) * 400;       % 截止频率
fp = fs1 - 100;             % 通带频率
rp = 0.2;                   % 通带波动
rs = 3;                     % 阻带衰减
ws = fs1/(fn/2);             % 归一化阻带频率
wp = fp/(fn/2);             % 归一化通带频率
% 产生带限高斯白噪声
u = wgn(1,N,0);                % 0dB高斯白噪声  
[g,Wn] = buttord(wp,ws,rp,rs);  % g：滤波器阶数，Wn：截止频率
[b,b1] = butter(g,Wn);           % 巴特沃斯低通滤波器
x0 = filter(b,b1,u);             % 高斯白噪声过低通滤波器

% 噪声调幅干扰
A = 1;
Kam = 2 + (p/100) * 8;                   % 调幅系数
f0 = randi([-0.1*Rs 0.1*Rs]);            % 干扰信号中心频率
theta = 2*pi*rand(1,1);                  % 随机相位
y2 = (A+Kam*x0).*exp(1j*(2*pi*f0*t+theta));
m2 = mean(abs(y2).^2);                                           
c = sqrt(power/m2);                                               
nam_sig = c*y2; 
end