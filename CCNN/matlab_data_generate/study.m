clc;
clear;
close all;
%% 通信
rs = 2e6;
fs = 10e6;
T = 0.01;
win = hamming(100,"symmetric");
x = TX_LFM(rs, 20, fs, T, 51);
y = PSK_MOD('QPSK', rs, 10, fs, T);
z = x + y;
N = length(z);
Hs = fftshift(abs(fft(z)));
f = (-N/2:N/2-1)*fs/N;
figure;
plot(real(z(1:5000)));
figure;
plot(f,Hs);
figure;
stft(z(1:5000), fs, 'Window',win,'OverlapLength',98,'FFTLength',128);

for i = 1:2
    for j = 1:3
        for k = 1:6
            for m = 1:100
                ISR = {6, 8, 10, 12, 14};
                signal_type = {'BPSK'; 'QPSK'; '8PSK'};
                inte_type = {'LFM', 'MTJ', 'NAM', 'NFM', 'SIN', 'STJ'};
                 % 保存为.mat文件
                filepath = ['C:\Users\m1889\Desktop\project\干扰信号识别\信号识别\signal\matlab_data_generate\data\' ...
                           signal_type{i} '_' inte_type{k} '_' ...
                           num2str(ISR{j}) '_' num2str(m) '.mat'];
                
                signal = PSK_MOD(signal_type{i}, rs, 10, fs, T);
                if k == 1
                    inte = TX_LFM(rs, 10+ISR{j}, fs, T, m);
                elseif k == 2
                    inte = TX_MTJ(rs, 10+ISR{j}, fs, T);
                elseif k == 3
                    inte = TX_NAM(rs, 10+ISR{j}, fs, T, m);
                elseif k == 4
                    inte = TX_NFM(rs, 10+ISR{j}, fs, T, m);
                elseif k == 5
                    inte = TX_SIN(rs, 10+ISR{j}, fs, T, m);
                elseif k == 6
                    inte = TX_STJ(rs, 10+ISR{j}, fs, T, m);
                end
                data = signal + inte;

              %  save(filepath, 'data'); % 保存变量名为'data'
            end
        end
    end
end

% for i = 1:3
%     for j = 1:5
%         for k = 1:1
%             for m = 1:100
%                 ISR = {6, 8, 10, 12, 14};
%                 signal_type = {'BPSK'; 'QPSK'; '8PSK'};
%                 inte_type = {'LFM'};
%                 filepath = ['C:\Users\16648\Desktop\newdata\5M\LFMnew\' signal_type{i} '_' inte_type{k} '_' num2str(ISR{j})  '_' num2str(m) '.wv'];
%                 signal = PSK_MOD(signal_type{i}, rs, 10, fs, T);
%                 inte = TX_LFM(rs, 10+ISR{j}, fs, T, m);
%                 data = signal + inte;
%                 iqtowv(real(data), imag(data), filepath);
%             end
%         end
%     end
% end
%% 雷达
% fs = 10e6;
% br = 3e6;
% T = 0.01;
% m = 1;
% win = hamming(100,"symmetric");
% N = randi([5, 13]); % 位数
% Binary_code = randi([0, 1], 1, N);
% x = LD_WDTJ('LFM', br, 16, fs, T, N, Binary_code, m);
% y = LD_MOD('LFM', br, 10, fs, T, N, Binary_code, m);
% z = x + y;
% N = length(z);
% Hs = fftshift(abs(fft(z)));
% f = (-N/2:N/2-1)*fs/N;
% figure;
% plot(real(z(1:5000)));
% figure;
% plot(f,Hs);
% figure;
% stft(z(1:5000), fs, 'Window',win,'OverlapLength',98,'FFTLength',128);

% for i = 1:2
%     for j = 1:5
%         for k = 1:5
%             for m = 1:100
%                 ISR = {6, 8, 10, 12, 14};
%                 signal_type = {'LFM'; 'BPSK'};
%                 inte_type = {'CN', 'NP', 'IS', 'WDTJ', 'COMB'};
%                 filepath = ['C:\Users\16648\Desktop\newdata\5M\雷达\' signal_type{i} '_' inte_type{k} '_' num2str(ISR{j})  '_' num2str(m) '.wv'];
%                 br = 2e6 + m * 1e4;
%                 N = randi([5, 13]); % 位数
%                 Binary_code = randi([0, 1], 1, N);
%                 signal = LD_MOD(signal_type{i}, br, 10, fs, T, N, Binary_code, m);
%                 if k == 1
%                     inte = LD_CN(signal_type{i}, br, 10+ISR{j}, fs, T, N, Binary_code, m);
%                 elseif k == 2
%                     inte = LD_NP(signal_type{i}, (br-1.5e6), 10+ISR{j}, fs, T, N, Binary_code, m);
%                 elseif k == 3
%                     inte = LD_IS(signal_type{i}, br, 10+ISR{j}, fs, T, N, Binary_code, m);
%                 elseif k == 4
%                     inte = LD_WDTJ(signal_type{i}, br, 10+ISR{j}, fs, T, N, Binary_code, m);
%                 elseif k == 5
%                     inte = LD_COMB(signal_type{i}, br, 10+ISR{j}, fs, T, N, Binary_code, m);
%                 end
%                 data = signal + inte;
%                 iqtowv(real(data), imag(data), filepath);
%             end
%         end
%     end
% end


function iqtowv(I_data, Q_data, PATH)
    IQInfo.I_data = I_data;   % #I-data(1*n) from mat file
    IQInfo.Q_data = Q_data;   % #Q-data(1*n) from mat file
    IQInfo.clock  = 10E6;   % #Sample Rate 
    IQInfo.filename = PATH;
    % #Plot Data for preview
%     rs_visualize( IQInfo.clock, IQInfo.I_data, IQInfo.Q_data );
    
    % #generate *.wv file
    rs_generate_wave(0, IQInfo, 0, 1)   % #generate the wv file
    disp(['waveform file "' IQInfo.filename '" saved...']);
end