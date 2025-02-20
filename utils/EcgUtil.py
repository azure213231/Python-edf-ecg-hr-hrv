import numpy as np
import pyedflib
import neurokit2 as nk

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

# 计算心率和 HRV
# 计算 HRV 和心率的正确方式
def compute_hr_hrv_30s(ecg_signal, sampling_rate):
    """
    计算每 30 秒的平均心率（bpm）和 HRV 指标（仅 RMSSD），
    若 RMSSD 计算异常，则置为 -1。

    参数：
    - ecg_signal: ECG 原始信号（一维数组）
    - sampling_rate: 采样率（Hz）

    返回：
    - hr_list: 每个 30s 片段的平均心率（bpm）数组
    - hrv_list: 每个 30s 片段的 RMSSD 值数组
    """
    segment_duration = 30  # 30 秒
    segment_samples = int(segment_duration * sampling_rate)
    total_samples = len(ecg_signal)
    n_segments = total_samples // segment_samples

    hr_list = []
    hrv_list = []

    for i in range(n_segments):
        start = i * segment_samples
        end = start + segment_samples
        segment = ecg_signal[start:end]

        # 处理 ECG 信号，提取 R 波
        try:
            # 处理 ECG 信号，去噪
            ecg_cleaned, info = nk.ecg_process(segment, sampling_rate=sampling_rate)
            r_peaks = info["ECG_R_Peaks"]
        except Exception as e:
            print(f"片段 {i + 1} 处理失败")
            hr_list.append(-1)
            hrv_list.append(-1)
            continue

        # 如果 R 波过少，跳过
        if len(r_peaks) < 3:
            hr_list.append(-1)
            hrv_list.append(-1)
            continue

        # **计算平均心率**
        rr_intervals = np.diff(r_peaks) / sampling_rate  # 计算 RR 间期（秒）

        # 基于标准差过滤异常 R-R 间期
        filtered_rr_intervals_filter = filter_rr_by_change(rr_intervals, change_threshold=0.2)

        # 如果 RR 间期长度小于或等于 5，跳过此片段
        if len(filtered_rr_intervals_filter) > 3:
            # 计算平均心率
            avg_hr = round(60 / np.mean(filtered_rr_intervals_filter), 2) if len(filtered_rr_intervals_filter) > 0 else -1
            # **提取 RMSSD**
            # 确保 filtered_rr_intervals_std 是一个 NumPy 数组
            filtered_rr_intervals_filter = np.array(filtered_rr_intervals_filter)
            # 将每个元素乘以 1000
            filtered_rr_intervals_ms = filtered_rr_intervals_filter * 1000
            rmssd = calculate_rmssd(filtered_rr_intervals_ms)
            if rmssd > 200:
                print("rmssd > 200")
        else:
            avg_hr = -1
            rmssd = -1

        # 存储结果
        hr_list.append(avg_hr)
        hrv_list.append(rmssd)

        print(f"片段 {i+1}: 心率 = {avg_hr:.2f}, RMSSD = {rmssd}")

    return hr_list, hrv_list