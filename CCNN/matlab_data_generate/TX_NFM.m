%% 噪声调频（NFM）
% rs:码元速率；power:功率/dBw；fs：采样率；t:采样时长
function nfm_sig = TX_NFM(rs, power, fs, T, randd)
Rs = rs;                          % 码元速率
N = fs * T;                        % 采样点数
Fs = fs;                           % 采样率
t = 0:1/Fs:(N-1)*(1/Fs);           % 时间轴
power = 10.^(power/10);
p = randd;
% 滤波器系数
fn = 10000;                 % 采样频率
fs1 = 150 + (p/100) * 50;       % 截止频率
fp = fs1 - 100;              % 通带频率
rp = 0.2;                    % 通带波动
rs = 3;                      % 阻带衰减
ws = fs1/(fn/2);              % 归一化阻带频率
wp = fp/(fn/2);              % 归一化通带频率
% 产生带限高斯白噪声
u = wgn(1,N,-10);               % -10dB高斯白噪声  
[g,Wn] = buttord(wp,ws,rp,rs);   % g：滤波器阶数，Wn：截止频率
[b,b1] = butter(g,Wn);           % 巴特沃斯低通滤波器
x0 = filter(b,b1,u);             % 高斯白噪声过低通滤波器
% 噪声调频干扰
sum(1)=0;                     % 定义法求积分
for i = 1:N-1             
    sum(i+1) = x0(i)+sum(i);
end
xn = sum;
Kfm = 0.3 + (p/100) * 0.4;                  % 调频系数
f0 = randi([-0.1*Rs 0.1*Rs]);          % 干扰信号中心频率
theta = 2*pi*rand(1,1);                % 随机相位
A = sqrt(power);
y2 = A*exp(1j*(2*pi*f0*t+2*pi*Kfm*xn+theta));
m2 = mean(abs(y2).^2);                                           
c = sqrt(power/m2);                                               
nfm_sig = c*y2; 
end