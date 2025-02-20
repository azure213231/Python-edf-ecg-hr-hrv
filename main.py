# This is a sample Python script.
import os

import numpy as np
from rich.layout import Layout
from rich.panel import Panel

from utils.EcgUtil import compute_hr_hrv_30s
from utils.FileUtils import get_files, read_edf, save_to_csv, find_matching_xml, extract_sleep_stages
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.text import Text
import time

console = Console()

def main():
    # edf_dir = "D:\\EDF\\shhs\\test_data\\edf"
    # xml_dir = "D:\\EDF\\shhs\\test_data\\xml"
    # output_dir = "D:\\EDF\\shhs\\test_data\\csv"
    edf_dir = "Y:\\3-AI\\1-PSG-dataSet\\nsrr\\shhs\\polysomnography\\edfs\\shhs1"
    xml_dir = "Y:\\3-AI\\1-PSG-dataSet\\nsrr\\shhs\\polysomnography\\annotations-events-profusion\\shhs1"
    output_dir = "Y:\\3-AI\\1-PSG-dataSet\\nsrr\\shhs\\polysomnography\\csv-3-hml\\shhs1-hr-hrv"

    edf_files = get_files(edf_dir, ".edf")
    xml_files = get_files(xml_dir, ".xml")
    edf_file_count = len(edf_files)
    xml_file_count = len(xml_files)
    print(f"找到的edf文件数量为：{edf_file_count}, xml的数量为： {xml_file_count}")

    success_file_count = 0
    fail_file_count = 0

    # 使用 Live 来固定显示一行并更新内容
    with Live(console=console, refresh_per_second=1) as live:
        for idx, (root, filename) in enumerate(edf_files, start=1):
            filepath = os.path.join(root, filename)
            progress = round(idx / edf_file_count, 4)

            # 更新进度
            live.update(f"处理文件 {idx}/{edf_file_count}: {filename}, progress: {round(progress, 4)}, "
                        f"success_count: {success_file_count}, fail_count: {fail_file_count}")

            # 获取文件名（不带路径和扩展名）
            base_filename = os.path.splitext(filename)[0]
            # 使用文件名作为输出CSV文件名
            output_file = os.path.join(output_dir, f"{base_filename}.csv")
            try:
                # 找到对应的xml文件
                xml_path, xml_file = find_matching_xml(filename, xml_files)
                if not xml_file:
                    fail_file_count += 1
                    print(f"警告：未找到与 {filename} 对应的XML文件")
                    continue
                full_xml_path = os.path.join(xml_path, xml_file)
                sleep_stage_list = extract_sleep_stages(full_xml_path)
                if len(sleep_stage_list) < 100:
                    fail_file_count += 1
                    print(f"数据长度不足，丢弃")
                    continue

                signals, sampling_rates = read_edf(filepath, channels=["ECG"])
                ecg_signal = signals["ECG"]
                fs = sampling_rates["ECG"]
                print("ECG信号长度：", len(ecg_signal), "采样率：", fs)
                hr_list, hrv_list = compute_hr_hrv_30s(ecg_signal, fs)

                # 假设 hr_list, hrv_list, sleep_stage_list 已经生成
                min_len = min(len(hr_list), len(hrv_list), len(sleep_stage_list))
                print(f"心率长度：{len(hr_list)}, HRV长度：{len(hrv_list)}，睡眠阶段长度: {len(sleep_stage_list)}")
                if min_len > 100:
                    print(f"使用最短长度：{min_len} 来裁剪数据")
                    # 对三个列表进行裁剪
                    hr_list = hr_list[:min_len]
                    hrv_list = hrv_list[:min_len]
                    sleep_stage_list = sleep_stage_list[:min_len]

                    save_to_csv(hr_list, hrv_list, sleep_stage_list, output_file)
                    success_file_count += 1
                else:
                    fail_file_count += 1
                    print(f"数据长度不足，丢弃")

            except Exception as e:
                fail_file_count += 1
                print(f"处理文件 {filepath} 时出错: {e}")

if __name__ == '__main__':
    main()
