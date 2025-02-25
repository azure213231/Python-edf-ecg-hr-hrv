import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pyedflib
import neurokit2 as nk
from rich.console import Console

console = Console()

def calculate_rmssd(rr_intervals):
    # 计算R-R间隔差值
    rr_diff = np.diff(rr_intervals)

    # 计算平方差值
    rr_diff_squared = np.square(rr_diff)

    # 计算平方差值的平均值
    mean_squared_diff = np.mean(rr_diff_squared)

    # 计算RMSSD值并保留2位小数
    rmssd = np.sqrt(mean_squared_diff)
    return round(rmssd, 2)


def filter_rr_by_change(rr_intervals, change_threshold=0.2):
    rr_intervals = np.array(rr_intervals)
    # 设定合理范围（单位：秒）
    rr_min, rr_max = 0.5, 1.4  # 低于 300ms，高于 2000ms 的值视为异常
    rr_intervals = rr_intervals[(rr_intervals >= rr_min) & (rr_intervals <= rr_max)]

    # 初始化循环
    while True:
        if len(rr_intervals) < 3:
            break  # 太少的数据不需要筛选

        median_rr = np.median(rr_intervals)
        # 计算相邻 R-R 之间的变化率
        rr_diff = np.abs(np.diff(rr_intervals)) / rr_intervals[:-1]

        # 比较首尾元素（与第一个和最后一个元素的相邻元素比较）
        first_diff = np.abs(rr_intervals[0] - median_rr) / median_rr

        # 合并首尾元素的变化率
        rr_diff = np.concatenate(([first_diff], rr_diff))

        # 过滤掉变化率超过阈值的 R-R 间期
        valid_indices = np.where(rr_diff <= change_threshold)[0]

        # 获取新的 R-R 间期
        filtered_rr = rr_intervals[valid_indices]

        # 如果没有变化，停止过滤
        if len(filtered_rr) == len(rr_intervals):
            break

        # 否则，更新 R-R 间期数据，继续过滤
        rr_intervals = filtered_rr

    return rr_intervals

def compute_hr_hrv_by_rr(i, rr_intervals):
    filtered_rr_intervals = filter_rr_by_change(rr_intervals, change_threshold=0.2)

    if len(filtered_rr_intervals) > 5:
        avg_hr = round(60 / np.mean(filtered_rr_intervals), 2) if len(filtered_rr_intervals) > 0 else -1
        filtered_rr_intervals_ms = np.array(filtered_rr_intervals) * 1000
        rmssd = calculate_rmssd(filtered_rr_intervals_ms)
        print(f"片段 {i + 1}: 心率 = {avg_hr:.2f}, RMSSD = {rmssd}")
        return avg_hr, rmssd
    else:
        return -1, -1  # 片段太短或数据有问题，返回None


def process_segment(i, ecg_signal, sampling_rate, segment_samples):
    start = i * segment_samples
    end = start + segment_samples
    segment = ecg_signal[start:end]

    try:
        ecg_cleaned, info = nk.ecg_process(segment, sampling_rate=sampling_rate)
        r_peaks = info["ECG_R_Peaks"]
    except Exception as e:
        print(f"片段 {i + 1} 处理失败: {e}")
        return []  # 返回 None 表示该片段处理失败

    if len(r_peaks) < 5:
        return []  # 如果R波过少，返回None

    rr_intervals = np.diff(r_peaks) / sampling_rate

    # avg_hr, rmssd = compute_hr_hrv_by_rr(i, rr_intervals)
    # return avg_hr, rmssd

    print(f"片段 {i + 1}: rr长度 = {len(rr_intervals)}")
    rr_intervals = np.array(rr_intervals) * 1000
    return rr_intervals

def compute_hr_hrv_30s(ecg_signal, sampling_rate):
    segment_duration = 30  # 30秒
    segment_samples = int(segment_duration * sampling_rate)
    total_samples = len(ecg_signal)
    n_segments = total_samples // segment_samples

    hr_list = []
    hrv_list = []

    # 使用进程池并行化处理每个片段
    with ProcessPoolExecutor() as executor:
        # 提交任务并获取结果
        futures = [executor.submit(process_segment, i, ecg_signal, sampling_rate, segment_samples) for i in
                   range(n_segments)]

        # 获取每个片段的处理结果
        for future in futures:
            result = future.result()  # 获取任务结果
            avg_hr, rmssd = result
            hr_list.append(avg_hr)
            hrv_list.append(rmssd)

    return hr_list, hrv_list

def compute_rr_30s(ecg_signal, sampling_rate):
    segment_duration = 30  # 30秒
    segment_samples = int(segment_duration * sampling_rate)
    total_samples = len(ecg_signal)
    n_segments = total_samples // segment_samples
    print(f"总片段数: {n_segments}")
    rr_list = []

    max_workers = multiprocessing.cpu_count()  # 获取CPU核心数
    # 使用进程池并行化处理每个片段
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交任务并获取结果
        futures = [executor.submit(process_segment, i, ecg_signal, sampling_rate, segment_samples) for i in
                   range(n_segments)]

        # 获取每个片段的处理结果
        for future in futures:
            result = future.result()  # 获取任务结果
            rr_intervals = result
            rr_list.append(rr_intervals)

    return rr_list