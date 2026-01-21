import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import os


def get_date_ranges(years: int = 10) -> List[tuple]:
    """
    将时间范围按12个月分段
    
    Args:
        years: 获取近N年的数据，默认10年
    
    Returns:
        日期范围列表，每个元素为 (start_date, end_date) 格式为 YYYY-MM-DD
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    date_ranges = []
    current_start = start_date
    
    while current_start < end_date:
        # 计算12个月后的日期
        current_end = current_start + timedelta(days=365)
        # 如果超过结束日期，使用结束日期
        if current_end > end_date:
            current_end = end_date
        
        date_ranges.append((
            current_start.strftime("%Y-%m-%d"),
            current_end.strftime("%Y-%m-%d")
        ))
        
        # 移动到下一个时间段（从当前结束日期的下一天开始）
        current_start = current_end + timedelta(days=1)
    
    return date_ranges


def fetch_fund_data(fund_code: str, start_date: str, end_date: str, page_no: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """
    获取基金历史数据
    
    Args:
        fund_code: 基金代码
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        page_no: 页码，从1开始
        page_size: 每页数据量，默认10
    
    Returns:
        API响应的JSON数据
    """
    url = "https://www.bosera.com/fund/fundHisDetail.json"
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.bosera.com',
        'Referer': f'https://www.bosera.com/fund/{fund_code}.html',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }
    
    data = {
        'pageNo': str(page_no),
        'pageSize': str(page_size),
        'fundCode': fund_code,
        'startDate': start_date,
        'endDate': end_date
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        raise


def get_all_fund_data(fund_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取指定时间范围内的所有基金数据（自动处理分页）
    
    Args:
        fund_code: 基金代码
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
    
    Returns:
        所有数据的列表
    """
    all_data = []
    page_no = 1
    page_size = 10
    
    print(f"  获取时间段 {start_date} 至 {end_date} 的数据...")
    
    while True:
        try:
            print(f"    正在获取第 {page_no} 页...", end=" ")
            response_data = fetch_fund_data(fund_code, start_date, end_date, page_no, page_size)
            
            # 检查响应数据
            if not response_data or 'data' not in response_data:
                print("响应数据格式异常")
                break
            
            result_list = response_data.get('data', []).get('resultList', [])
            
            if not result_list:
                print("没有更多数据")
                break
            
            all_data.extend(result_list)
            print(f"获取到 {len(result_list)} 条数据，累计 {len(all_data)} 条")
            
            # 如果返回的数据少于page_size，说明已经是最后一页
            if len(result_list) < page_size:
                break
            
            page_no += 1
            # 添加短暂延迟，避免请求过快
            time.sleep(0.5)
            
        except Exception as e:
            print(f"获取第 {page_no} 页数据失败: {e}")
            break
    
    return all_data


def convert_percentage(value: Any) -> float:
    """
    将百分比值转换为小数形式（用于Excel百分数格式）
    
    Args:
        value: 百分比值（可能是字符串、数字或None）
    
    Returns:
        转换为小数后的值（如5.5% -> 0.055），如果无法转换则返回None
    """
    if value is None or value == "":
        return None
    
    try:
        # 如果是字符串，去掉百分号
        if isinstance(value, str):
            value = value.replace("%", "").strip()
            if not value:
                return None
        
        # 转换为浮点数
        num_value = float(value)
        
        # 如果数值较大（如大于1），可能是百分比形式（如5.5表示5.5%），需要除以100
        # 如果数值较小（如小于等于1），可能已经是小数形式（如0.055表示5.5%）
        # 这里假设API返回的是百分比形式（如5.5表示5.5%），所以除以100
        return num_value / 100.0
    except (ValueError, TypeError):
        return None


def process_fund_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    处理基金数据并转换为DataFrame
    
    Args:
        data: 原始数据列表
    
    Returns:
        DataFrame对象
    """
    rows = []
    
    for item in data:
        row = {
            "日期": item.get("date", ""),
            "单位净值(元)": item.get("netValuePer", ""),
            "日涨跌(%)": convert_percentage(item.get("rate", "")),
            "最近7天收益率(%)": convert_percentage(item.get("weekYield", "")),
            "最近30日收益率(%)": convert_percentage(item.get("monthYield", "")),
            "今年以来收益率(%)": convert_percentage(item.get("thisYearYield", "")),
            "成立以来收益率(%)": convert_percentage(item.get("totalYield", "")),
            "累计净值(元)": item.get("totalNetValue", "")
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # 按日期排序（从早到晚）
    if not df.empty and "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"], errors='coerce')
        df = df.sort_values("日期", ascending=True)
        df["日期"] = df["日期"].dt.strftime("%Y-%m-%d")
    
    return df


def export_fund_to_excel(fund_code: str = "159937", years: int = 10, output_file: str = None):
    """
    导出基金数据到Excel文件
    
    Args:
        fund_code: 基金代码，默认159937（博时黄金ETF）
        years: 获取近N年的数据，默认10年
        output_file: 输出文件路径，如果为None则使用默认路径
    """
    if output_file is None:
        output_file = "output/博时黄金ETF数据.xlsx"
    
    # 确保output文件夹存在
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"开始获取博时黄金ETF ({fund_code}) 近 {years} 年的数据...")
    print("=" * 60)
    
    # 获取所有时间段
    date_ranges = get_date_ranges(years)
    print(f"共需要获取 {len(date_ranges)} 个时间段的数据\n")
    
    # 存储所有数据
    all_data = []
    
    # 遍历每个时间段
    for idx, (start_date, end_date) in enumerate(date_ranges, 1):
        print(f"[{idx}/{len(date_ranges)}] ", end="")
        try:
            data = get_all_fund_data(fund_code, start_date, end_date)
            all_data.extend(data)
            print(f"  时间段完成，累计获取 {len(all_data)} 条数据\n")
        except Exception as e:
            print(f"  时间段获取失败: {e}\n")
            continue
        
        # 添加延迟，避免请求过快
        if idx < len(date_ranges):
            time.sleep(1)
    
    if not all_data:
        print("未获取到任何数据，无法生成Excel文件")
        return
    
    print("=" * 60)
    print(f"数据获取完成，共获取 {len(all_data)} 条数据")
    print("正在处理数据并保存到Excel...")
    
    # 处理数据
    df = process_fund_data(all_data)
    
    # 保存到Excel
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            # 获取工作表对象
            worksheet = writer.sheets['Sheet1']
            
            # 定义百分比列
            percentage_columns = [
                "日涨跌(%)",
                "最近7天收益率(%)",
                "最近30日收益率(%)",
                "今年以来收益率(%)",
                "成立以来收益率(%)"
            ]
            
            # 获取列索引
            column_indices = {col: df.columns.get_loc(col) for col in percentage_columns if col in df.columns}
            
            # 应用百分数格式
            for col_name, col_idx in column_indices.items():
                # 列索引从0开始，但Excel列索引从1开始，所以需要+1
                # 行索引从2开始（第1行是标题，第2行开始是数据）
                for row_idx in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row_idx, column=col_idx + 1)
                    # 设置百分数格式（保留2位小数）
                    cell.number_format = '0.00%'
        
        print(f"\n✓ 数据已成功保存到: {output_file}")
        print(f"共 {len(df)} 条记录")
        if not df.empty:
            print(f"日期范围: {df['日期'].iloc[0]} 至 {df['日期'].iloc[-1]}")
    except Exception as e:
        print(f"保存Excel文件失败: {e}")
        raise


if __name__ == "__main__":
    # 导出博时黄金ETF数据
    export_fund_to_excel(fund_code="159937", years=10)
    print("\n所有数据导出完成！")
