import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import math
import time
import itertools
import sys
import io

# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import torch
import numpy as np
from torch import nn
from math import sqrt
import matplotlib.pyplot as plt
import matplotlib
from torch.utils.data import Dataset, DataLoader
# # ------------------
# import torch.multiprocessing
# # ------------------
from scipy.fftpack import fft, fftshift

matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
matplotlib.rcParams['font.family']='sans-serif'
matplotlib.rcParams['axes.unicode_minus'] = False  # 正确显示负号

class CNN(nn.Module):
    def __init__(self, out_channels):     #  初始化函数
        super(CNN, self).__init__()
        self.out_channels = out_channels
        self.conv1 = nn.Conv1d(in_channels=2, out_channels=int(self.out_channels / 2), kernel_size=3, stride=2,
                               padding=1)  #长度减半
        self.bn1 = nn.BatchNorm1d(int(self.out_channels / 2))    #  批归一化层，加速网络训练
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv1d(in_channels=int(self.out_channels / 2), out_channels=int(self.out_channels / 2),
                               kernel_size=3,
                               stride=2, padding=1)
        self.bn2 = nn.BatchNorm1d(int(self.out_channels / 2))
        self.relu2 = nn.ReLU()
        self.pool2 = nn.AvgPool1d(kernel_size=8, stride=2)
        self.conv3 = nn.Conv1d(in_channels=int(self.out_channels / 2), out_channels=self.out_channels,
                               kernel_size=3,
                               stride=3, padding=1)
        self.bn3 = nn.BatchNorm1d(self.out_channels)
        self.relu3 = nn.ReLU()
        # self.conv4 = nn.Conv1d(in_channels=int(self.out_channels / 2), out_channels=self.out_channels,
        #                        kernel_size=3,
        #                        stride=1, padding=1)
        # self.bn4 = nn.BatchNorm1d(self.out_channels)
        # self.relu4 = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        out = self.conv1(x)      #  2500
        out = self.bn1(out)
        out = self.relu1(out)
        out = self.conv2(out)    #  1250
        out = self.bn2(out)
        out = self.pool2(out)    #  622
        out = self.relu2(out)
        out = self.conv3(out)    #  208
        out = self.bn3(out)
        out = self.relu3(out)
        out = self.dropout(out)
        # out = self.conv4(out)
        # out = self.bn4(out)
        # out = self.relu4(out)
        # print(out.shape)
        return out


class SELayer(nn.Module):                  #  通道注意力机制
    def __init__(self, channels, reduction):     #channels: 输入特征图的通道数，reduction: 用于缩减通道数的因子
        super(SELayer, self).__init__()
        self.s = nn.AdaptiveAvgPool1d(1)   #  创建一个全局平均池化层，将每个通道的特征压缩为1个数值，每个通道只保留1个值
        self.e = nn.Sequential(
            nn.Linear(channels, channels // reduction),    #  第一个线性层，将通道数从 channels 减少到 channels // reduction
            nn.ReLU(),
            nn.Linear(channels // reduction, channels),   #  第二个线性层，将通道数从 channels // reduction 恢复到 channels
            nn.Sigmoid()
        )
        #  通过两步降维和升维操作，生成每个通道的权重
    def forward(self, x):
        b, c, _ = x.size()                             #获取输入的 batch size 和通道数
        y = self.s(x).view(b, c)                       #(batch_size, channels)
        y = self.e(y).view(b, c, 1)                   #  生成注意力权重
        out = x * y.expand_as(x)                      #  将权重 y 通过 expand_as(x) 扩展到与输入 x 的形状相同（即 (batch_size, channels, length)，对每个通道进行加权调整
        return out


class ResNet(nn.Module):
    def __init__(self, in_channels=128, out_channels=32, reduction=16):
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv1d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv1d(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.se = SELayer(out_channels, reduction)
        self.conv3 = nn.Conv1d(in_channels=in_channels, out_channels=out_channels, kernel_size=1, stride=1, padding=0)
        self.relu = nn.ReLU()

    def forward(self, x):
        _x = x

        x = self.conv1(x)
        x = self.relu1(x)
        x = self.conv2(x)
        x = self.se(x)

        _x = self.conv3(_x)
        # print(_x.shape)
        # print(x.shape)
        out = x + _x

        return self.relu(out)


class CausalConv1d(nn.Module):                 #  因果卷积，用于时间序列
    def __init__(self, in_channels, out_channels, kernel_size, stride, dilation=1):
        super(CausalConv1d, self).__init__()
        self.pad = (kernel_size - 1) * dilation    # 计算所需的填充
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, stride,
                               padding=self.pad, dilation=dilation, bias=True)

    def forward(self, x):
        x = self.conv1(x)
        x = x[..., :-self.pad]
        #  在最后一个维度（序列长度）上进行截取，去掉卷积后填充的部分（未来的无效信息）。
        return x

# def generate_decreasing_random_array(size, start=0.05, stop=0.03):
#     if size <= 1:
#         return np.array([np.random.uniform(start, stop)])
#
#     step = (start - stop) / (size - 1)
#     return np.array([start - i * step + np.random.uniform(-step/2, 0) for i in range(size)])

class MHA(nn.Module):                  #  多头注意力机制，增强模型对全局和局部信息的捕捉能力
    dim_in: int  # 输入的维度大小
    dim_q: int  # query dimension
    dim_k: int  # key  dimension
    dim_v: int  # value dimension
    num_heads: int  # number of heads

    def __init__(self, dim_in, dim_q, dim_k, dim_v, num_heads=4):
        super(MHA, self).__init__()
        self.dim_in = dim_in
        self.dim_q = dim_q
        self.dim_k = dim_k
        self.dim_v = dim_v
        self.num_heads = num_heads

        self.Causal_conv_q = CausalConv1d(in_channels=32, out_channels=32, kernel_size=7, stride=1)
        self.Causal_conv_k = CausalConv1d(in_channels=32, out_channels=32, kernel_size=7, stride=1)
        self.Causal_conv_v = CausalConv1d(in_channels=32, out_channels=32, kernel_size=7, stride=1)

        self._norm_fact = 1 / sqrt(dim_k // num_heads)
        #  计算归一化因子_norm_fact，用于缩放点积注意力的结果，将 dim_k 除以 num_heads，然后取平方根倒数，以防止大数值的点积带来数值不稳定问题
    def forward(self, x):
        batch, n, dim_in = x.shape          #batch，32，208
        nh = self.num_heads
        dq = self.dim_q // nh  # dim_q of each head  52
        dk = self.dim_k // nh  # dim_k of each head  52
        dv = self.dim_v // nh  # dim_v of each head  52
        # print(self.Causal_conv_q(x).shape)
        q = self.Causal_conv_q(x).reshape(batch, n, nh, dq).transpose(1, 2)  # (batch, nh, n, dk)：(1000, 4, 32, 52)
        k = self.Causal_conv_k(x).reshape(batch, n, nh, dk).transpose(1, 2)  # (batch, nh, n, dk)
        v = self.Causal_conv_v(x).reshape(batch, n, nh, dv).transpose(1, 2)  # (batch, nh, n, dv)

        dist = torch.matmul(q, k.transpose(2, 3)) * self._norm_fact  # (batch, nh, n, n)：(1000, 4, 32, 32)
        #  使用 torch.matmul 进行查询和键的矩阵乘法，得到点积注意力的分数。这里将键向量 k 进行转置，以便进行矩阵乘法
        #  乘以归一化因子 _norm_fact，确保点积结果不会因为维度过大而数值不稳定
        #  结果的形状为 (batch, nh, n, n)，表示每个头的注意力分数
        dist = torch.softmax(dist, dim=-1)  # (batch, nh, n, n)
        #  对点积结果进行 softmax 操作，沿着最后一个维度归一化，得到注意力权重。每个头对于序列中每个位置的关注程度通过权重表示
        att = torch.matmul(dist, v)  # (batch, nh, n, dv)
        #  使用计算出的注意力权重 dist 加权值向量 v，得到加权后的输出。形状为 (batch, nh, n, dv)，表示每个注意力头加权后的值
        att = att.transpose(1, 2).reshape(batch, n, self.dim_v)  # (batch, n, dim_v)
        #  将加权后的结果进行转置恢复原始形状，并通过 reshape 调整为 (batch, n, self.dim_v)，表示多头注意力的最终输出

        return att


class FeedForward(nn.Module):                  #  前馈神经网络
    def __init__(self):
        super(FeedForward, self).__init__()
        self.fc1 = nn.Linear(208, 32)
        self.fc2 = nn.Linear(32, 208)

    def forward(self, x):
        out = self.fc1(x)
        out = self.fc2(out)
        return out


class TCC_mod(nn.Module):                  #类似于 Transformer 的基础组件
    def __init__(self):
        super(TCC_mod, self).__init__()
        self.MHA = MHA(dim_in=208, dim_q=208, dim_k=208, dim_v=208)
        self.ln1 = nn.LayerNorm(208)                    #层标准化
        self.ff = FeedForward()
        self.ln2 = nn.LayerNorm(208)

    def forward(self, x):
        residual1 = x
        out = self.MHA(x)
        out += residual1
        out = self.ln1(out)
        residual2 = out
        out = self.ff(out)
        out += residual2
        out = self.ln2(out)
        return out


class Classifier_mod(nn.Module):
    def __init__(self, num_classes):
        super(Classifier_mod, self).__init__()
        self.pool = nn.AvgPool1d(32)
        self.fc1 = nn.Linear(192, 16)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=0.1)
        self.fc2 = nn.Linear(16, num_classes)

    def forward(self, x):
        out = self.pool(x)
        out = out.view(out.shape[0], -1)              #(batch_size, 192*32=6656)
        out = self.fc1(out)                         #(batch_size, 16)
        out = self.relu(out)                         #(batch_size, 16)
        out = self.dropout(out)                        #(batch_size, 16)
        out = self.fc2(out)                             # (batch, num_classes)
        # print(out.shape)
        return out


class CCNN(nn.Module):                                #types = ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ', 'SIN']
    def __init__(self, num_classes):
        super(CCNN, self).__init__()
        self.CNN = CNN(out_channels=128)
        self.resnet = ResNet()
        self.TCC = TCC_mod()
        self.Classifier = Classifier_mod(num_classes)

    def forward(self, x):
        x = x.view(x.size(0), 2, -1)
        out = self.CNN(x)     #batch 128 208
        out = self.resnet(out)   #batch 32 208
        out = self.TCC(out)       #batch 32 208
        out = self.Classifier(out)   #batch class_num
        return out



class MyDataset(Dataset):
    def __init__(self, roots):
        data_list = []
        label_list = []
        for root in roots:
            f = np.load(root)
            data = f['data']
            # 转换为复数用于功率计算
            data_complex = data[:, 0, :] + 1j * data[:, 1, :]
            
            data_list.append(f["data"])
            label_list.append(f["label"])

        self.input = torch.from_numpy(np.concatenate(data_list)).type(torch.FloatTensor)
        # ✅ 修复：使用 LongTensor 用于 CrossEntropyLoss
        self.label = torch.from_numpy(np.concatenate(label_list)).type(torch.LongTensor)
        
        print(f"✓ 数据集加载完成: 输入 {self.input.shape}, 标签 {self.label.shape}")

    def __getitem__(self, index):
        input_data = self.input[index]  # (2, 5000)
        label = self.label[index]       # 标量，整数类型
        
        # 转换为复数进行功率计算
        data_complex = input_data[0, :] + 1j * input_data[1, :]
        
        # 功率归一化
        power = torch.mean(torch.abs(data_complex) ** 2)
        power_normalized_input = input_data / torch.sqrt(power)
        
        return power_normalized_input, label

    def __len__(self):
        return self.input.shape[0]

def initialize_weights(m):  # 初始化神经网络中的层权重
    classname = m.__class__.__name__  # 获取传入模块的类名，存储在变量 classname 中。这用于判断模块的类型（如 Conv2d 或 Linear）。
    if classname.find('Conv2d') != -1:  # 检查 classname 是否包含字符串 'Conv2d'。如果是，说明模块 m 是一个二维卷积层。
        nn.init.xavier_uniform_(m.weight.data)  # 如果 m 是一个卷积层，使用 Xavier 均匀初始化方法初始化其权重。
        nn.init.constant_(m.bias.data, 0.0)  # 将卷积层的偏置项初始化为 0
    elif classname.find('Linear') != -1:
        nn.init.xavier_uniform_(m.weight)
        nn.init.constant_(m.bias, 0.0)


def epoch_time(start_time, end_time):
    elapsed_time = end_time - start_time
    elapsed_mins = int(elapsed_time / 60)
    elapsed_secs = int(elapsed_time - (elapsed_mins * 60))
    return elapsed_mins, elapsed_secs


def confusion_matrix(preds, labels, conf_matrix):
    for p, t in zip(preds, labels):
        conf_matrix[p, t] += 1
    return conf_matrix


def plot_confusion_matrix(cm, classes, normalize=False, title='Confusion matrix', cmap=plt.cm.Blues):
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')
    print(cm)
    # plt.imshow(cm, interpolation='nearest', cmap=cmap)
    # plt.title(title)
    # plt.colorbar()
    # tick_marks = np.arange(len(classes))
    # plt.xticks(tick_marks, classes, rotation=45)
    # plt.yticks(tick_marks, classes)
    #
    # plt.axis("equal")
    # ax = plt.gca()
    # left, right = plt.xlim()
    # ax.spines['left'].set_position(('data', left))
    # ax.spines['right'].set_position(('data', right))
    # for edge_i in ['top', 'bottom', 'right', 'left']:
    #     ax.spines[edge_i].set_edgecolor("white")
    #
    # thresh = cm.max() / 2.
    # for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
    #     num = '{:.2f}'.format(cm[i, j]) if normalize else int(cm[i, j])
    #     plt.text(i, j, num,
    #              verticalalignment='center',
    #              horizontalalignment="center",
    #              color="white" if num > thresh else "black")
    # plt.tight_layout()
    # plt.ylabel('True label')
    # plt.xlabel('Predicted label')
    # plt.show()

def plot_trainperformance(train_losses, test_losses, train_accuracies, test_accuracies, save_path=None):
    epochs = range(1, len(train_losses) + 1)
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, 'b-', label='Training loss')
    plt.plot(epochs, test_losses, 'r-', label='Validation loss')
    plt.title('训练损失和验证损失')
    plt.xlabel('训练轮数')
    plt.ylabel('损失')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(epochs, train_accuracies, 'b-', label='Training accuracy')
    plt.plot(epochs, test_accuracies, 'r-', label='Validation accuracy')
    plt.title('训练准确率和验证准确率')
    plt.xlabel('训练轮数')
    plt.ylabel('准确率')
    plt.legend()

    plt.tight_layout()
    
    # 保存图表
    if save_path is None:
        save_path = 'training_performance.png'
    plt.savefig(save_path, dpi=100)
    print(f"\n✓ 训练性能图表已保存: {save_path}")
    plt.close()
    # return plt

# def plot_testaccuracy(accuracies, snr_values):
#     plt.figure(figsize=(10, 5))
#     plt.plot(snr_values, accuracies, 'o-', color='blue')
#     plt.title('准确率vs干信比')
#     plt.xlabel('干信比 (dB)')
#     plt.ylabel('准确率')
#     plt.grid(True)
#     plt.xticks(snr_values)
#     plt.show()

def plot_types_accuracy(type_accuracies, snr_values, types, save_path=None):
    plt.figure(figsize=(10, 5))

    for type_name, accuracies in type_accuracies.items():
        plt.plot(snr_values, accuracies, 'o-', label=type_name)  # 为每个类型绘制曲线

    plt.title('各类型信号准确率 vs 干信比')
    plt.xlabel('干信比 (dB)')
    plt.ylabel('准确率')
    plt.legend()  # 显示图例
    # plt.grid(True)
    plt.xticks(snr_values)
    
    # 保存图表
    if save_path is None:
        save_path = 'types_accuracy.png'
    plt.savefig(save_path, dpi=100)
    print(f"✓ 类型准确率图表已保存: {save_path}")
    plt.close()
    # return plt
def train_epoch(model, loader, opt, device='cpu'):
    model.train()
    epoch_loss = 0
    loss_fn = nn.CrossEntropyLoss()
    train_acc = 0
    for i, (data, label) in enumerate(loader):
        data, label = data.to(device), label.to(device)

        # print("label", label)
        # 前向传播
        out = model(data)
        loss = loss_fn(out, label.long())
        # loss = loss_fn(out, label)
        epoch_loss += loss.item()
        # 正确率计算
        # print(out.shape)
        # print(label.shape)
        train_accuracy = (out.argmax(-1) == label).sum() / label.shape[0]
        train_acc += train_accuracy
        # 反向传播
        opt.zero_grad()
        loss.backward()
        opt.step()

    return epoch_loss / len(loader), train_acc / len(loader)


def test_epoch(model, loader, types, device='cpu'):
    model.eval()
    epoch_loss = 0
    loss_fn = nn.CrossEntropyLoss()
    test_acc = 0
    # 混淆矩阵初始化
    L = len(types)
    conf_matrix = torch.zeros(L, L).to(device)
    with torch.no_grad():
        for i, (data, label) in enumerate(loader):
            data, label = data.to(device), label.to(device)
            # print(label)
            # 前向传播
            out = model(data)
            loss = loss_fn(out, label.long())
            epoch_loss += loss.item()
            # 混淆矩阵
            conf_matrix = confusion_matrix(out.argmax(1), labels=label.long(), conf_matrix=conf_matrix)
            # 正确率计算
            test_accuracy = (out.argmax(1) == label).sum() / label.shape[0]
            test_acc += test_accuracy
    # 每种类型的准确率
    conf_matrix = conf_matrix.numpy()
    types_num = np.sum(conf_matrix, axis=0)
    types_acc = np.diagonal(conf_matrix) / types_num
    # 画混淆矩阵
    plot_confusion_matrix(conf_matrix, classes=types, normalize=False,
                          title='Normalized confusion matrix')
    # random_decrements = generate_decreasing_random_array(len(types))
    # types_acc_adjusted = np.maximum(types_acc - random_decrements, 0)
    # return epoch_loss / len(loader), test_acc / len(loader), types_acc_adjusted
    return epoch_loss / len(loader), test_acc / len(loader), types_acc


def train_process(model, loader_train, loader_test, opt, epochs, types, model_path,
                  best_acc, best_types_acc, device='cpu'):
    train_losses, test_losses, train_accuracies, test_accuracies = [], [], [], []
    try:
        for step in range(epochs):
            start_time = time.time()
            train_loss, train_acc = train_epoch(model=model, loader=loader_train, opt=opt, device=device)
            test_loss, test_acc, types_acc = test_epoch(model=model, loader=loader_test, types=types, device=device)
            end_time = time.time()
            train_losses.append(train_loss)
            test_losses.append(test_loss)
            train_accuracies.append(train_acc.item())  # Use .item() to get a Python float
            test_accuracies.append(test_acc.item())
            epoch_mins, epoch_secs = epoch_time(start_time, end_time)
            # 打印训练过程
            print(f'Epoch: {step + 1} | Time: {epoch_mins}m {epoch_secs}s')
            print(f'\tTrain Loss: {"%.8f" % train_loss}  Train Acc: {"%.6f" % train_acc}')
            print(f'\tVal Loss: {"%.8f" % test_loss}  Val Acc: {"%.6f" % test_acc}')
            for i in range(len(types)):
                print(f'\tModulation Type: {types[i]}  Type Acc: {"%.6f" % types_acc.tolist()[i]}')
            # # 保存模型
            # if (test_acc > best_acc) & (train_acc > best_acc):
            #     if (types_acc > best_types_acc).all():
            #         best_acc = test_acc
            #         torch.save(model.state_dict(), model_path.format(test_acc))
            #         print(f'\tModel saved')
            # 保存模型
            save_path = model_path.format(step + 1, test_acc)
            torch.save(model.state_dict(), save_path)
            print(f'\tModel saved at epoch {step + 1} with val acc {test_acc:.6f}')
            # 更新最佳准确率
            if test_acc >= best_acc:
                best_acc = test_acc
                best_types_acc = types_acc
    except KeyboardInterrupt:
        print("Training interrupted")
    finally:
        plot_trainperformance(train_losses, test_losses, train_accuracies, test_accuracies)

def train_run(class_num, lr, bath_size, epochs, types, best_acc, best_types_acc,
              train_paths, test_path, model_path, device='cpu'):
    # #--------------------
    # torch.multiprocessing.set_sharing_strategy('file_system')
    # #--------------------
    # 模型实例化
    model = CCNN(num_classes=class_num)
    model = model.to(device)
    model.apply(initialize_weights)
    # print(model)
    total_params = sum(p.numel() for p in model.parameters())
    print(f'{total_params:,} total parameters.')
    # 优化器
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    # 训练集
    data = MyDataset(train_paths)
    # print(data)
    train_size = int(0.8 * len(data))
    test_size = len(data) - train_size
    train_data, test_data = torch.utils.data.random_split(data, [train_size, test_size])

    loader_train = DataLoader(train_data, batch_size=bath_size, shuffle=True)
    loader_test = DataLoader(test_data, batch_size=bath_size, shuffle=True)
    train_process(model=model, loader_train=loader_train, loader_test=loader_test,
                  opt=opt, epochs=epochs, types=types, model_path=model_path,
                  best_acc=best_acc, best_types_acc=best_types_acc, device=device)


def test_run(class_num, types, bath_size, model_path, test_paths, snr_values, device='cpu'):

    model = CCNN(num_classes=class_num)
    model = model.to(device)
    model.load_state_dict(torch.load(model_path))
    # accuracies = []
    type_accuracies = {type_name: [] for type_name in types}  # 创建字典存储每种类型的准确率
    # print(model)
    for i in range(len(test_paths)):
        test_data = MyDataset(test_paths[i])
        print("test_label:", test_data.label)
        print("test_len:", len(test_data))
        loader_test = DataLoader(test_data, batch_size=bath_size, shuffle=True)
        test_loss, test_acc, types_acc = test_epoch(model=model, loader=loader_test, types=types)
        for type_name, acc in zip(types, types_acc):
            type_accuracies[type_name].append(acc.item())  # 添加每个类型的准确率
        print(f'Test: {i + 1}')
        print(f'\tTest Loss: {"%.8f" % test_loss}  Test Acc: {"%.6f" % test_acc}')
        print(f'\tTypes:{types} Types Acc: {np.round(types_acc, 6)}')
    #     accuracies.append(test_acc.item())
    # plot_testaccuracy(accuracies, snr_values)
    plot_types_accuracy(type_accuracies, snr_values, types)

def test_page(class_num, types, bath_size, model_path, test_path):
    model = CCNN(num_classes=class_num)
    model = model.cuda()
    model.load_state_dict(torch.load(model_path))

    # 加载测试数据
    test_data = MyDataset(test_path)
    loader_test = DataLoader(test_data, batch_size=bath_size, shuffle=True)

    model.eval()
    type_counts = {type_name: 0 for type_name in types}

    with torch.no_grad():
        for i, (data, label) in enumerate(loader_test):
            # 调整数据形状：[batch_size, length, channels] -> [batch_size, channels, length]
            data = data.transpose(1, 2).to(device)
            label = label.to(device)

            out = model(data)
            preds = out.argmax(1)

            for type_index, type_name in enumerate(types):
                type_counts[type_name] += torch.sum(preds == type_index).item()

    for type_name, count in type_counts.items():
        print(f'Modulation Type: {type_name}, Count: {count}')


# ✅ 增强版的 SignalDataset，支持数据增强
class SignalDataset(Dataset):
    def __init__(self, npz_path, augment=False):
        """
        初始化信号数据集
        
        参数:
            npz_path: .npz文件路径
            augment: 是否进行数据增强 (默认False)
        """
        data = np.load(npz_path)
        self.signals = data['data']  # 形状: (N, 2, 5000)
        self.labels = data['label']  # 形状: (N,)
        self.augment = augment
        
        # 转换为PyTorch张量
        self.signals = torch.from_numpy(self.signals).float()
        self.labels = torch.from_numpy(self.labels).long()  # ✅ 正确的类型
        
        print(f"✓ 数据集加载完成: 信号 {self.signals.shape}, 标签 {self.labels.shape}")
    
    def __len__(self):
        return len(self.signals)
    
    def __getitem__(self, idx):
        signal = self.signals[idx]  # 形状: (2, 5000)
        label = self.labels[idx]
        
        # 转换为复数并进行功率归一化
        complex_signal = signal[0] + 1j * signal[1]
        power = torch.mean(torch.abs(complex_signal) ** 2)
        normalized_signal = signal / torch.sqrt(power)
        
        # ✅ 数据增强
        if self.augment:
            normalized_signal = self._augment_signal(normalized_signal)
        
        return normalized_signal, label
    
    def _augment_signal(self, signal):
        """对信号进行数据增强"""
        # 随机选择增强方式
        augment_type = np.random.randint(0, 5)
        
        if augment_type == 0:
            # 频率偏移
            signal = self._frequency_shift(signal)
        elif augment_type == 1:
            # 时间缩放
            signal = self._time_scale(signal)
        elif augment_type == 2:
            # 相位旋转
            signal = self._phase_rotate(signal)
        elif augment_type == 3:
            # 幅度缩放
            signal = self._amplitude_scale(signal)
        elif augment_type == 4:
            # 添加噪声
            signal = self._add_noise(signal)
        
        return signal
    
    def _frequency_shift(self, signal, fs=10e6):
        """频率偏移 (±5kHz)"""
        freq_shift = np.random.uniform(-5e3, 5e3)
        t = torch.arange(signal.shape[-1], dtype=torch.float32) / fs
        phase_shift = 2 * np.pi * freq_shift * t
        
        complex_signal = signal[0] + 1j * signal[1]
        shifted = complex_signal * torch.exp(1j * torch.tensor(phase_shift, dtype=torch.complex64))
        
        return torch.stack([torch.real(shifted), torch.imag(shifted)])
    
    def _time_scale(self, signal):
        """时间缩放 (0.9 ~ 1.1倍)"""
        from torch.nn.functional import interpolate
        scale = np.random.uniform(0.9, 1.1)
        new_length = int(signal.shape[-1] * scale)
        
        # 使用插值改变长度
        scaled = interpolate(
            signal.unsqueeze(0), 
            size=new_length, 
            mode='linear', 
            align_corners=False
        ).squeeze(0)
        
        # 确保长度为5000
        if scaled.shape[-1] < 5000:
            pad = torch.zeros(scaled.shape[0], 5000 - scaled.shape[-1])
            scaled = torch.cat([scaled, pad], dim=-1)
        else:
            scaled = scaled[:, :5000]
        
        return scaled
    
    def _phase_rotate(self, signal):
        """相位旋转 (0 ~ 360度)"""
        angle_deg = np.random.uniform(0, 360)
        angle_rad = np.radians(angle_deg)
        
        complex_signal = signal[0] + 1j * signal[1]
        rotated = complex_signal * torch.exp(torch.tensor(1j * angle_rad, dtype=torch.complex64))
        
        return torch.stack([torch.real(rotated), torch.imag(rotated)])
    
    def _amplitude_scale(self, signal):
        """幅度缩放 (0.8 ~ 1.2倍)"""
        scale = np.random.uniform(0.8, 1.2)
        return signal * scale
    
    def _add_noise(self, signal, snr_db=15):
        """添加高斯白噪声"""
        signal_power = torch.mean(torch.abs(signal[0] + 1j * signal[1]) ** 2)
        noise_power = signal_power / (10 ** (snr_db / 10))
        
        noise = torch.randn_like(signal) * torch.sqrt(noise_power)
        return signal + noise
# ✅ 改进的测试函数，包含详细的性能评估
def test_model_comprehensive(model, data_loader, class_names, device='cpu'):
    """
    完整的模型测试函数，包含混淆矩阵和各类型准确率
    
    参数:
        model: 训练好的模型
        data_loader: 数据加载器
        class_names: 类别名称列表
        device: 运行设备 ('cpu' 或 'cuda')
    """
    model.eval()
    model = model.to(device)
    
    all_preds = []
    all_labels = []
    total_correct = 0
    total_samples = 0
    
    with torch.no_grad():
        for signals, labels in data_loader:
            signals = signals.to(device)
            labels = labels.to(device)
            
            outputs = model(signals)
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
            total_correct += (preds == labels).sum().item()
            total_samples += labels.size(0)
    
    # 计算整体准确率
    overall_accuracy = total_correct / total_samples * 100
    print(f"\n{'='*60}")
    print(f"总体准确率: {overall_accuracy:.2f}%")
    print(f"总样本数: {total_samples}, 正确预测: {total_correct}")
    print(f"{'='*60}\n")
    
    # 计算混淆矩阵
    conf_matrix = np.zeros((len(class_names), len(class_names)))
    for pred, label in zip(all_preds, all_labels):
        conf_matrix[int(pred), int(label)] += 1
    
    # 打印混淆矩阵
    print("混淆矩阵:")
    print("        " + "  ".join(f"{name:>8}" for name in class_names))
    for i, class_name in enumerate(class_names):
        row_str = f"{class_name:>8}: " + "  ".join(
            f"{conf_matrix[i, j]:>8.0f}" for j in range(len(class_names))
        )
        print(row_str)
    
    # 计算各类型的准确率
    print(f"\n{'='*60}")
    print("各类型准确率:")
    print(f"{'='*60}")
    for i, class_name in enumerate(class_names):
        type_samples = np.sum(conf_matrix[:, i])
        if type_samples > 0:
            type_acc = conf_matrix[i, i] / type_samples * 100
            print(f"{class_name:>8}: {type_acc:>6.2f}% ({int(conf_matrix[i, i])}/{int(type_samples)})")
    print(f"{'='*60}\n")
    
    return overall_accuracy, conf_matrix, all_preds, all_labels


# ✅ 改进的文件夹测试函数
def test_model_with_npz_files(model, folder_path, batch_size, class_names, device='cpu'):
    """
    遍历文件夹中所有npz文件进行测试
    
    参数:
        model: 训练好的模型
        folder_path: 包含npz文件的文件夹路径
        batch_size: 批处理大小
        class_names: 类别名称列表
        device: 运行设备
    """
    model.eval()
    model = model.to(device)
    
    # 获取所有npz文件
    npz_files = sorted([
        os.path.join(folder_path, f) 
        for f in os.listdir(folder_path) 
        if f.endswith('.npz')
    ])
    
    if not npz_files:
        print(f"❌ 错误: 在 {folder_path} 中未找到 .npz 文件")
        return
    
    print(f"✓ 找到 {len(npz_files)} 个测试文件\n")
    
    # 遍历所有文件
    all_results = []
    for npz_file in npz_files:
        print(f"处理文件: {os.path.basename(npz_file)}")
        print("-" * 70)
        
        try:
            # 加载数据集
            test_dataset = SignalDataset(npz_file, augment=False)
            test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
            
            # 运行测试
            with torch.no_grad():
                correct = 0
                total = 0
                file_preds = []
                file_labels = []
                
                for signals, labels in test_loader:
                    signals = signals.to(device)
                    labels = labels.to(device)
                    
                    outputs = model(signals)
                    _, preds = torch.max(outputs, 1)
                    
                    file_preds.extend(preds.cpu().numpy())
                    file_labels.extend(labels.cpu().numpy())
                    
                    correct += (preds == labels).sum().item()
                    total += labels.size(0)
                
                accuracy = correct / total * 100
                file_result = {
                    'file': os.path.basename(npz_file),
                    'accuracy': accuracy,
                    'correct': correct,
                    'total': total,
                    'preds': file_preds,
                    'labels': file_labels
                }
                all_results.append(file_result)
                
                print(f"✓ 文件准确率: {accuracy:.2f}% ({correct}/{total})")
                
                # 显示部分预测结果
                for i in range(min(5, len(file_preds))):
                    true_name = class_names[int(file_labels[i])]
                    pred_name = class_names[int(file_preds[i])]
                    status = "✓" if file_labels[i] == file_preds[i] else "✗"
                    print(f"  样本{i+1}: 真实={true_name:>6}, 预测={pred_name:>6} {status}")
        
        except Exception as e:
            print(f"❌ 处理文件时出错: {e}")
        
        print()
    
    # 汇总结果
    print(f"\n{'='*70}")
    print("测试汇总")
    print(f"{'='*70}")
    for result in all_results:
        print(f"{result['file']:>40}: {result['accuracy']:>6.2f}%")
    
    avg_accuracy = np.mean([r['accuracy'] for r in all_results])
    print(f"{'平均准确率':>40}: {avg_accuracy:>6.2f}%")
    print(f"{'='*70}\n")
    
    return all_results


def main():
    """
    主函数：支持训练、测试、推理等操作
    """
    import argparse
    
    # 获取脚本所在目录（CCNN目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description='CCNN 干扰信号识别')
    parser.add_argument('--mode', type=str, choices=['train', 'test', 'infer'], 
                        default='infer', help='运行模式')
    parser.add_argument('--model-path', type=str, 
                        default=os.path.join(script_dir, '..', '..', '2_models', 'best', 'ccnn_epoch_86_acc_0.9913.pth'), help='模型路径')
    parser.add_argument('--data-path', type=str, 
                        default=os.path.join(script_dir, '..', '..', '1_datasets', 'train'), help='数据路径')
    parser.add_argument('--batch-size', type=int, default=32, help='批大小')
    parser.add_argument('--num-classes', type=int, default=6, 
                        help='类别数 (5=旧模型, 6=新模型支持SIN)')
    parser.add_argument('--device', type=str, choices=['cpu', 'cuda'], 
                        default='cuda' if torch.cuda.is_available() else 'cpu',
                        help='运行设备')
    
    args = parser.parse_args()
    
    # 根据类别数设置信号类型
    if args.num_classes == 5:
        class_names = ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ']
    else:
        class_names = ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ', 'SIN']
    
    class_num = args.num_classes
    
    print(f"✓ 使用设备: {args.device}")
    print(f"✓ 模式: {args.mode}\n")
    
    if args.mode == 'train':
        # 训练模式
        print("启动训练模式...")
        model = CCNN(num_classes=class_num)
        model = model.to(args.device)
        model.apply(initialize_weights)
        
        # 获取训练数据路径
        train_data_dir = os.path.join(script_dir, 'data')
        train_paths = []
        
        if os.path.exists(train_data_dir):
            # 收集所有npz文件
            for file in os.listdir(train_data_dir):
                if file.endswith('.npz'):
                    train_paths.append(os.path.join(train_data_dir, file))
        
        if not train_paths:
            print(f"❌ 错误: 找不到训练数据")
            print(f"   请确保数据存在于: {train_data_dir}")
            return
        
        try:
            model_save_path = os.path.join(script_dir, 'model', 'ccnn_epoch_{}_acc_{:.4f}.pth')
            train_run(
                class_num=class_num,
                lr=0.001,
                bath_size=32,
                epochs=100,
                types=class_names,
                best_acc=0,
                best_types_acc=np.zeros(class_num),
                train_paths=train_paths,
                test_path=None,
                model_path=model_save_path,
                device=args.device
            )
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    elif args.mode == 'test':
        # 测试模式
        print("启动测试模式...")
        model = CCNN(num_classes=class_num)
        
        try:
            model.load_state_dict(torch.load(args.model_path, map_location=args.device))
            print(f"✓ 模型已加载: {args.model_path}")
        except FileNotFoundError:
            print(f"❌ 错误: 模型文件不存在: {args.model_path}")
            return
        
        model = model.to(args.device)
        
        # 测试文件夹
        test_results = test_model_with_npz_files(
            model=model,
            folder_path=args.data_path,
            batch_size=args.batch_size,
            class_names=class_names,
            device=args.device
        )
    
    elif args.mode == 'infer':
        # 推理模式（默认）
        print("启动推理模式...")
        model = CCNN(num_classes=class_num)
        
        # 尝试加载模型
        if os.path.exists(args.model_path):
            try:
                model.load_state_dict(torch.load(args.model_path, map_location=args.device))
                print(f"✓ 模型已加载: {args.model_path}")
            except Exception as e:
                print(f"⚠️  加载模型时出错: {e}")
                print("   使用未训练的模型进行推理...")
        else:
            print(f"⚠️  模型文件不存在: {args.model_path}")
            print("   使用未训练的模型进行推理...")
        
        model = model.to(args.device)
        
        # 推理
        if os.path.isdir(args.data_path):
            test_model_with_npz_files(
                model=model,
                folder_path=args.data_path,
                batch_size=args.batch_size,
                class_names=class_names,
                device=args.device
            )
        elif os.path.isfile(args.data_path):
            # 单个文件推理
            try:
                dataset = SignalDataset(args.data_path)
                data_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
                test_model_comprehensive(model, data_loader, class_names, args.device)
            except Exception as e:
                print(f"❌ 错误: {e}")
        else:
            print(f"❌ 错误: 数据路径不存在: {args.data_path}")

if __name__ == "__main__":
    main()
