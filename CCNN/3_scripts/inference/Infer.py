import os
from torch.utils.data import Dataset, DataLoader
import torch
import acl
import numpy as np
from PIL import Image

ACL_MEM_MALLOC_HUGE_FIRST = 0
ACL_MEMCPY_HOST_TO_DEVICE = 1
ACL_MEMCPY_DEVICE_TO_HOST = 2


class net:
    def __init__(self, model_path):
        # 初始化函数
        self.device_id = 0

        # step1: 初始化
        ret = acl.init()
        print("初始化ret=",ret)
        # 指定运算的Device
        ret = acl.rt.set_device(self.device_id)

        # step2: 加载模型，本示例为ResNet-50模型
        # 加载离线模型文件，返回标识模型的ID
        self.model_id, ret = acl.mdl.load_from_file(model_path)
        # 创建空白模型描述信息，获取模型描述信息的指针地址
        self.model_desc = acl.mdl.create_desc()
        # 通过模型的ID，将模型的描述信息填充到model_desc
        ret = acl.mdl.get_desc(self.model_desc, self.model_id)

        # step3：创建输入输出数据集
        # 创建输入数据集
        self.input_dataset, self.input_data = self.prepare_dataset('input')
        # 创建输出数据集
        self.output_dataset, self.output_data = self.prepare_dataset('output')

    def prepare_dataset(self, io_type):
       # 准备数据集
       if io_type == "input":
           # 获得模型输入的个数
           io_num = acl.mdl.get_num_inputs(self.model_desc)
           acl_mdl_get_size_by_index = acl.mdl.get_input_size_by_index
       else:
           # 获得模型输出的个数
           io_num = acl.mdl.get_num_outputs(self.model_desc)
           acl_mdl_get_size_by_index = acl.mdl.get_output_size_by_index
       # 创建aclmdlDataset类型的数据，描述模型推理的输入。
       dataset = acl.mdl.create_dataset()
       datas = []
       for i in range(io_num):
           # 获取所需的buffer内存大小
           buffer_size = acl_mdl_get_size_by_index(self.model_desc, i)
           # 申请buffer内存
           buffer, ret = acl.rt.malloc(buffer_size, ACL_MEM_MALLOC_HUGE_FIRST)
           # 从内存创建buffer数据
           data_buffer = acl.create_data_buffer(buffer, buffer_size)
           # 将buffer数据添加到数据集
           _, ret = acl.mdl.add_dataset_buffer(dataset, data_buffer)
           datas.append({"buffer": buffer, "data": data_buffer, "size": buffer_size})
       return dataset, datas


    def forward(self, inputs):
        # 执行推理任务
        # 遍历所有输入，拷贝到对应的buffer内存中
        input_num = len(inputs)
        for i in range(input_num):
            # 将PyTorch Tensor转换为NumPy数组
            if isinstance(inputs[i], torch.Tensor):
                # 重要：先移动到CPU并断开计算图
                numpy_array = inputs[i].cpu().detach().numpy()
            else:
                numpy_array = inputs[i]  # 如果已是NumPy数组则直接使用

            # 使用NumPy数组的tobytes()
            bytes_data = numpy_array.tobytes()  # ✅
            bytes_ptr = acl.util.bytes_to_ptr(bytes_data)
            ret = acl.rt.memcpy(self.input_data[i]["buffer"],
                                self.input_data[i]["size"],
                                bytes_ptr,
                                len(bytes_data),
                                ACL_MEMCPY_HOST_TO_DEVICE)
        # 执行模型推理。
        ret = acl.mdl.execute(self.model_id, self.input_dataset, self.output_dataset)
        # 处理模型推理的输出数据，输出top5置信度的类别编号。
        inference_result = []
        for i, item in enumerate(self.output_data):
            buffer_host, ret = acl.rt.malloc_host(self.output_data[i]["size"])
            # 将推理输出数据从Device传输到Host。
            ret = acl.rt.memcpy(buffer_host,  # 目标地址 host
                                self.output_data[i]["size"],  # 目标地址大小
                                self.output_data[i]["buffer"],  # 源地址 device
                                self.output_data[i]["size"],  # 源地址大小
                                ACL_MEMCPY_DEVICE_TO_HOST)  # 模式：从device到host
            # 从内存地址获取bytes对象
            bytes_out = acl.util.ptr_to_bytes(buffer_host, self.output_data[i]["size"])
            # 按照float32格式将数据转为numpy数组
            data = np.frombuffer(bytes_out, dtype=np.float32)
            inference_result.append(data)
        vals = np.array(inference_result).flatten()
        # 对结果进行softmax转换
        vals = np.exp(vals)
        vals = vals / np.sum(vals)
        return vals

    def __del__(self):
       # 析构函数 按照初始化资源的相反顺序释放资源。
       # 销毁输入输出数据集
       for dataset in [self.input_data, self.output_data]:
           while dataset:
               item = dataset.pop()
               ret = acl.destroy_data_buffer(item["data"])    # 销毁buffer数据
               ret = acl.rt.free(item["buffer"])              # 释放buffer内存
       ret = acl.mdl.destroy_dataset(self.input_dataset)      # 销毁输入数据集
       ret = acl.mdl.destroy_dataset(self.output_dataset)     # 销毁输出数据集
       # 销毁模型描述
       ret = acl.mdl.destroy_desc(self.model_desc)
       # 卸载模型
       ret = acl.mdl.unload(self.model_id)
       # 释放device
       ret = acl.rt.reset_device(self.device_id)
       # acl去初始化
       ret = acl.finalize()


import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


class MyDataset(Dataset):
    def __init__(self, roots):
        data_list = []
        label_list = []
        for root in roots:
            f = np.load(root)
            data = f['data']
            label = f['label']

            # 确保数据形状正确 (batch_size, 2, 5000)
            if data.ndim == 2:
                data = data.reshape(1, *data.shape)

            data_list.append(data)
            label_list.append(label)

        self.input = np.concatenate(data_list, axis=0)
        self.label = np.concatenate(label_list, axis=0)

        print(f"数据集加载完成: 输入形状 {self.input.shape}, 标签形状 {self.label.shape}")

    def __getitem__(self, index):
        input_data = self.input[index]  # 形状: (2, 5000)
        label = self.label[index]

        # 转换为复数并进行功率归一化
        complex_data = input_data[0] + 1j * input_data[1]
        power = np.mean(np.abs(complex_data) ** 2)
        normalized_data = input_data / np.sqrt(power)

        return normalized_data, label

    def __len__(self):
        return len(self.input)


def test_model_with_npz_files(ccnn_net, folder_path, batch_size, class_num, types):
    """测试模型性能

    参数:
        ccnn_net: 昇腾模型推理实例
        folder_path: 包含测试数据的文件夹
        batch_size: 批处理大小
        class_num: 类别数量
        types: 类别名称列表
    """
    # 获取文件夹中的所有 npz 文件
    npz_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.npz')]

    # 遍历所有 npz 文件
    for npz_file in npz_files:
        print(f"处理文件: {npz_file}")
        print("-" * 50)

        # 加载数据集
        test_dataset = MyDataset([npz_file])
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

        # 存储每个文件的统计结果
        total_samples = 0
        correct_predictions = 0

        # 处理每个批次
        for data, label in test_loader:
            # 将PyTorch张量转换为NumPy数组
            data_np = data.numpy()

            # 昇腾模型推理
            output = ccnn_net.forward([data_np])

            # 调试输出
            # print(f"模型输出: {output}")

            # 处理不同类型的输出
            if isinstance(output, list):
                # 如果输出是列表，取第一个元素
                output = output[0]

            if isinstance(output, np.ndarray):
                # 如果输出是数组，获取预测结果
                if output.ndim == 0:  # 标量数组
                    preds_np = np.array([int(output)])
                elif output.ndim == 1:  # 一维数组
                    if output.size == class_num:  # 概率分布
                        preds_np = np.argmax(output, axis=0)  # 获取最大概率索引
                        preds_np = np.array([preds_np])  # 转换为数组
                    else:  # 标签数组
                        preds_np = output.astype(int)
                else:  # 二维数组
                    preds_np = np.argmax(output, axis=1)
            elif isinstance(output, (float, np.floating)):
                # 如果输出是浮点数
                preds_np = np.array([int(output)])
            else:
                # 其他类型处理
                preds_np = np.array([int(output)])

            # 确保预测结果是整数
            preds_np = preds_np.astype(int)

            # 将标签转换为NumPy数组
            label_np = label.numpy().astype(int)

            # 统计正确预测
            batch_correct = np.sum(preds_np == label_np)
            correct_predictions += batch_correct
            total_samples += len(label_np)

            # 输出当前批次的预测结果
            for i in range(len(preds_np)):
                true_label = label_np[i]
                pred_label = preds_np[i]
                true_name = types[true_label]
                pred_name = types[pred_label]

                result = "✓" if true_label == pred_label else "✗"
                print(f"样本 {i + 1}: 真实: {true_name}({true_label}), 预测: {pred_name}({pred_label}) {result}")

        # 输出文件级别的统计结果
        accuracy = correct_predictions / total_samples * 100 if total_samples > 0 else 0
        print("\n" + "=" * 50)
        print(f"文件总结: {npz_file}")
        print(f"总样本数: {total_samples}, 正确预测: {correct_predictions}, 准确率: {accuracy:.2f}%")
        print("=" * 50 + "\n")


def main():
    # 初始化模型 - 这里假设您有一个net类用于加载.om模型
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, '..', '..', '2_models', 'archive', 'TXCCNNmodel1013.om')
    ccnn_net = net(model_path)

    # 数据路径和类别
    data_dir = os.path.join(script_dir, '..', '..', '1_datasets', 'raw')
    types = ['LFM', 'MTJ', 'NAM', 'NFM', 'STJ']

    # 测试模型
    test_model_with_npz_files(ccnn_net, data_dir, batch_size=1, class_num=5, types=types)


if __name__ == "__main__":
    main()
