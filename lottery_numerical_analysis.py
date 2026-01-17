import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from collections import Counter
import numpy as np
import os

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False


def analyze_dlt(file_path):
    """分析大乐透数据"""
    print(f"正在读取大乐透数据: {file_path}")
    df = pd.read_excel(file_path, engine='openpyxl')
    
    # 统计前区5个号码各数字出现次数
    front_area_numbers = []
    for col in ['前区1', '前区2', '前区3', '前区4', '前区5']:
        if col in df.columns:
            front_area_numbers.extend(df[col].astype(str).tolist())
    
    # 统计后区2个号码各数字出现次数
    back_area_numbers = []
    for col in ['后区1', '后区2']:
        if col in df.columns:
            back_area_numbers.extend(df[col].astype(str).tolist())
    
    # 过滤掉空值和无效值
    front_area_numbers = [int(x) for x in front_area_numbers if str(x).isdigit()]
    back_area_numbers = [int(x) for x in back_area_numbers if str(x).isdigit()]
    
    front_counter = Counter(front_area_numbers)
    back_counter = Counter(back_area_numbers)
    
    # 计算每期的平均值并添加到DataFrame
    front_avgs = []
    back_avgs = []
    all_avgs = []
    
    for idx, row in df.iterrows():
        front_values = []
        back_values = []
        all_values = []
        
        # 前区5个号码
        for col in ['前区1', '前区2', '前区3', '前区4', '前区5']:
            if col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).isdigit():
                    front_values.append(int(val))
                    all_values.append(int(val))
        
        # 后区2个号码
        for col in ['后区1', '后区2']:
            if col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).isdigit():
                    back_values.append(int(val))
                    all_values.append(int(val))
        
        if front_values and back_values and all_values:
            front_avgs.append(np.mean(front_values))
            back_avgs.append(np.mean(back_values))
            all_avgs.append(np.mean(all_values))
        else:
            front_avgs.append(np.nan)
            back_avgs.append(np.nan)
            all_avgs.append(np.nan)
    
    # 添加平均值列到DataFrame
    df['前区平均值'] = front_avgs
    df['后区平均值'] = back_avgs
    df['全部平均值'] = all_avgs
    
    # 计算所有期数总的平均值
    all_front_values = []
    all_back_values = []
    all_combined_values = []
    
    for idx, row in df.iterrows():
        for col in ['前区1', '前区2', '前区3', '前区4', '前区5']:
            if col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).isdigit():
                    all_front_values.append(int(val))
                    all_combined_values.append(int(val))
        
        for col in ['后区1', '后区2']:
            if col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).isdigit():
                    all_back_values.append(int(val))
                    all_combined_values.append(int(val))
    
    total_front_avg = np.mean(all_front_values) if all_front_values else 0
    total_back_avg = np.mean(all_back_values) if all_back_values else 0
    total_combined_avg = np.mean(all_combined_values) if all_combined_values else 0
    
    # 在最后一行添加总体平均值
    total_row_dict = {col: '' for col in df.columns}  # 先创建空行
    total_row_dict['期号'] = '总体平均值'
    total_row_dict['前区平均值'] = total_front_avg
    total_row_dict['后区平均值'] = total_back_avg
    total_row_dict['全部平均值'] = total_combined_avg
    total_row_df = pd.DataFrame([total_row_dict])
    df = pd.concat([df, total_row_df], ignore_index=True)
    
    # 保存到新的Excel文件（不覆盖原文件）
    base_name = os.path.splitext(file_path)[0]
    output_file = f"{base_name}_分析.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"平均值数据已保存到新文件: {output_file}")
    
    # 绘制统计图
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # 前区统计图
    front_nums = sorted(front_counter.keys())
    front_counts = [front_counter[n] for n in front_nums]
    bars1 = axes[0].bar(front_nums, front_counts, color='steelblue', alpha=0.7)
    axes[0].set_title('大乐透前区5个号码各数字出现次数统计', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('号码', fontsize=12)
    axes[0].set_ylabel('出现次数', fontsize=12)
    axes[0].set_xticks(front_nums)  # 确保所有x轴标签都显示
    axes[0].set_xticklabels(front_nums, rotation=0)
    axes[0].grid(axis='y', alpha=0.3)
    # 在柱状图顶部显示数值
    for bar in bars1:
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9)
    
    # 后区统计图
    back_nums = sorted(back_counter.keys())
    back_counts = [back_counter[n] for n in back_nums]
    bars2 = axes[1].bar(back_nums, back_counts, color='coral', alpha=0.7)
    axes[1].set_title('大乐透后区2个号码各数字出现次数统计', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('号码', fontsize=12)
    axes[1].set_ylabel('出现次数', fontsize=12)
    axes[1].set_xticks(back_nums)  # 确保所有x轴标签都显示
    axes[1].set_xticklabels(back_nums, rotation=0)
    axes[1].grid(axis='y', alpha=0.3)
    # 在柱状图顶部显示数值
    for bar in bars2:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('/Users/chenzhangjie/Downloads/大乐透统计图.png', dpi=300, bbox_inches='tight')
    print("统计图已保存到 大乐透统计图.png")
    plt.close()


def analyze_ssq(file_path):
    """分析双色球数据"""
    print(f"正在读取双色球数据: {file_path}")
    df = pd.read_excel(file_path, engine='openpyxl')
    
    # 统计红球6个号码各数字出现次数
    red_ball_numbers = []
    for col in ['红球1', '红球2', '红球3', '红球4', '红球5', '红球6']:
        if col in df.columns:
            red_ball_numbers.extend(df[col].astype(str).tolist())
    
    # 统计蓝球1个号码各数字出现次数
    blue_ball_numbers = []
    if '蓝球' in df.columns:
        blue_ball_numbers.extend(df['蓝球'].astype(str).tolist())
    
    # 过滤掉空值和无效值
    red_ball_numbers = [int(x) for x in red_ball_numbers if str(x).isdigit()]
    blue_ball_numbers = [int(x) for x in blue_ball_numbers if str(x).isdigit()]
    
    red_counter = Counter(red_ball_numbers)
    blue_counter = Counter(blue_ball_numbers)
    
    # 计算每期的平均值并添加到DataFrame
    red_avgs = []
    blue_avgs = []
    all_avgs = []
    
    for idx, row in df.iterrows():
        red_values = []
        blue_values = []
        all_values = []
        
        # 红球6个号码
        for col in ['红球1', '红球2', '红球3', '红球4', '红球5', '红球6']:
            if col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).isdigit():
                    red_values.append(int(val))
                    all_values.append(int(val))
        
        # 蓝球1个号码
        if '蓝球' in df.columns:
            val = row['蓝球']
            if pd.notna(val) and str(val).isdigit():
                blue_values.append(int(val))
                all_values.append(int(val))
        
        if red_values and blue_values and all_values:
            red_avgs.append(np.mean(red_values))
            blue_avgs.append(float(blue_values[0]) if blue_values else 0)
            all_avgs.append(np.mean(all_values))
        else:
            red_avgs.append(np.nan)
            blue_avgs.append(np.nan)
            all_avgs.append(np.nan)
    
    # 添加平均值列到DataFrame
    df['红球平均值'] = red_avgs
    df['蓝球平均值'] = blue_avgs
    df['全部平均值'] = all_avgs
    
    # 计算所有期数总的平均值
    all_red_values = []
    all_blue_values = []
    all_combined_values = []
    
    for idx, row in df.iterrows():
        for col in ['红球1', '红球2', '红球3', '红球4', '红球5', '红球6']:
            if col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).isdigit():
                    all_red_values.append(int(val))
                    all_combined_values.append(int(val))
        
        if '蓝球' in df.columns:
            val = row['蓝球']
            if pd.notna(val) and str(val).isdigit():
                all_blue_values.append(int(val))
                all_combined_values.append(int(val))
    
    total_red_avg = np.mean(all_red_values) if all_red_values else 0
    total_blue_avg = np.mean(all_blue_values) if all_blue_values else 0
    total_combined_avg = np.mean(all_combined_values) if all_combined_values else 0
    
    # 在最后一行添加总体平均值
    total_row_dict = {col: '' for col in df.columns}  # 先创建空行
    total_row_dict['期号'] = '总体平均值'
    total_row_dict['红球平均值'] = total_red_avg
    total_row_dict['蓝球平均值'] = total_blue_avg
    total_row_dict['全部平均值'] = total_combined_avg
    total_row_df = pd.DataFrame([total_row_dict])
    df = pd.concat([df, total_row_df], ignore_index=True)
    
    # 保存到新的Excel文件（不覆盖原文件）
    base_name = os.path.splitext(file_path)[0]
    output_file = f"{base_name}_分析.xlsx"
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"平均值数据已保存到新文件: {output_file}")
    
    # 绘制统计图
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # 红球统计图
    red_nums = sorted(red_counter.keys())
    red_counts = [red_counter[n] for n in red_nums]
    bars1 = axes[0].bar(red_nums, red_counts, color='red', alpha=0.7)
    axes[0].set_title('双色球红球6个号码各数字出现次数统计', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('号码', fontsize=12)
    axes[0].set_ylabel('出现次数', fontsize=12)
    axes[0].set_xticks(red_nums)  # 确保所有x轴标签都显示
    axes[0].set_xticklabels(red_nums, rotation=0)
    axes[0].grid(axis='y', alpha=0.3)
    # 在柱状图顶部显示数值
    for bar in bars1:
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9)
    
    # 蓝球统计图
    blue_nums = sorted(blue_counter.keys())
    blue_counts = [blue_counter[n] for n in blue_nums]
    bars2 = axes[1].bar(blue_nums, blue_counts, color='blue', alpha=0.7)
    axes[1].set_title('双色球蓝球1个号码各数字出现次数统计', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('号码', fontsize=12)
    axes[1].set_ylabel('出现次数', fontsize=12)
    axes[1].set_xticks(blue_nums)  # 确保所有x轴标签都显示
    axes[1].set_xticklabels(blue_nums, rotation=0)
    axes[1].grid(axis='y', alpha=0.3)
    # 在柱状图顶部显示数值
    for bar in bars2:
        height = bar.get_height()
        axes[1].text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('/Users/chenzhangjie/Downloads/双色球统计图.png', dpi=300, bbox_inches='tight')
    print("统计图已保存到 双色球统计图.png")
    plt.close()


if __name__ == "__main__":
    # 分析大乐透
    dlt_file = "/Users/chenzhangjie/Downloads/大乐透.xlsx"
    print("=" * 60)
    print("开始分析大乐透数据")
    print("=" * 60)
    try:
        analyze_dlt(dlt_file)
        print("大乐透分析完成！\n")
    except Exception as e:
        print(f"大乐透分析出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 分析双色球
    ssq_file = "/Users/chenzhangjie/Downloads/双色球.xlsx"
    print("=" * 60)
    print("开始分析双色球数据")
    print("=" * 60)
    try:
        analyze_ssq(ssq_file)
        print("双色球分析完成！\n")
    except Exception as e:
        print(f"双色球分析出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)
    print("所有分析完成！")
    print("=" * 60)
