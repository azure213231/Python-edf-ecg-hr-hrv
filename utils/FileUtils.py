import csv
import os
import re
import pyedflib
import xml.etree.ElementTree as ET
from rich.console import Console

console = Console()

def get_files(directory, extension) -> list:
    """
    递归获取目录及其子目录下指定扩展名的文件并按数字排序

    Args:
        directory (str): 目录路径
        extension (str): 文件扩展名

    Returns:
        list: 包含(子目录路径, 文件名)元组的排序列表
    """
    result = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(extension):
                # 保存(子目录路径, 文件名)元组
                result.append((root, f))
    # 按文件名中的数字排序
    return sorted(result, key=lambda x: int(re.search(r"\d+", x[1]).group()))


def read_edf(file_path, channels=None):
    """
    读取 EDF 文件中的指定通道信号。

    参数：
    - file_path: EDF 文件路径
    - channels: 要读取的通道名称，可以是字符串（单个通道）、列表（多个通道），或者为 None（读取所有通道）

    返回：
    - signals: 一个字典，键为通道名称，值为对应的信号数据
    - sampling_rates: 一个字典，键为通道名称，值为对应的采样率
    """
    f = pyedflib.EdfReader(file_path)
    channel_labels = f.getSignalLabels()

    # 如果未指定通道，默认读取所有通道
    if channels is None:
        channels = channel_labels
    # 如果传入单个通道名称，转换为列表
    elif isinstance(channels, str):
        channels = [channels]

    signals = {}
    sampling_rates = {}
    for ch in channels:
        if ch not in channel_labels:
            f.close()
            raise ValueError(f"通道 {ch} 未在 EDF 文件中找到")
        idx = channel_labels.index(ch)
        signals[ch] = f.readSignal(idx)
        sampling_rates[ch] = f.getSampleFrequency(idx)

    f.close()
    return signals, sampling_rates


def save_hr_hrv_to_csv(hr_list, hrv_list, sleep_stage_list, output_file):
    # 写入CSV文件
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)

        # 写入标题
        writer.writerow(["index", "timestamp", "heart_rate", "hrv", "sleep_stage"])

        # 写入数据
        for idx, (heart_rate, hrv, sleep_stage) in enumerate(zip(hr_list, hrv_list, sleep_stage_list), start=1):
            writer.writerow([idx , idx * 30, heart_rate, hrv, sleep_stage])

def save_rr_to_csv(rr_list, sleep_stage_list, output_file):
    # 写入CSV文件
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)

        # 写入标题
        writer.writerow(["index", "timestamp", "rr", "sleep_stage"])

        # 写入数据
        for idx, (rr, sleep_stage) in enumerate(zip(rr_list, sleep_stage_list), start=1):
            writer.writerow([idx, idx * 30, rr, sleep_stage])

def find_matching_xml(edf_filename, xml_files) -> tuple:
    """
    根据edf文件名找到对应的xml文件

    Args:
        edf_filename (str): edf文件名
        xml_files (list): 包含(路径,文件名)元组的xml文件列表

    Returns:
        tuple: 匹配的xml文件的(路径,文件名)元组，未找到则返回(None, None)
    """
    # 从edf文件名中提取编号部分
    edf_base = os.path.splitext(edf_filename)[0]  # 移除扩展名
    xml_pattern = f"{edf_base}-profusion.xml"

    for xml_path, xml_file in xml_files:
        if xml_file == xml_pattern:
            return (xml_path, xml_file)
    return (None, None)


def extract_sleep_stages(xml_file_path) -> list:
    """
    从XML文件中提取SleepStage的值

    Returns:
        list: 包含所有SleepStage值的列表

    Raises:
        FileNotFoundError: 当XML文件不存在时
        ET.ParseError: 当XML解析出错时
    """
    # 解析XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    sleep_stages = []
    # 使用 .// 进行递归查找所有层级中的元素
    for stage in root.findall(f".//SleepStage"):
        sleep_stages.append(int(stage.text))

    return sleep_stages