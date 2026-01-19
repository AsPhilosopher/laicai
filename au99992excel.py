import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re
from urllib.parse import urlencode

def parse_percentage(value):
    """解析百分比字符串为浮点数"""
    if pd.isna(value) or value == '':
        return None
    if isinstance(value, str):
        # 移除百分号并转换为浮点数
        return float(value.replace('%', '')) / 100
    return float(value)

def parse_number(value):
    """解析带逗号的数字字符串为浮点数"""
    if pd.isna(value) or value == '':
        return None
    if isinstance(value, str):
        # 移除逗号和其他非数字字符（保留负号）
        cleaned = re.sub(r'[^\d.-]', '', value)
        if cleaned == '':
            return None
        return float(cleaned)
    return float(value)

def get_gold_data(start_date, end_date, cookies=None):
    """
    获取黄金数据
    :param start_date: 开始日期 (YYYY-MM-DD)
    :param end_date: 结束日期 (YYYY-MM-DD)
    :param cookies: 可选的cookies
    :return: 包含黄金数据的DataFrame
    """
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'Referer': f'https://en.sge.com.cn/data/data_daily_international_new?start_date={start_date}&end_date={end_date}&inst_ids=Au99.99',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }
    
    if cookies:
        headers['Cookie'] = cookies
    
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'inst_ids': 'Au99.99',
        'p': 1  # 只获取第一页
    }
    
    url = f"https://en.sge.com.cn/data/data_daily_international_new?{urlencode(params)}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找表格
        table = soup.find('table')
        if not table:
            print(f"未找到表格，请求日期范围: {start_date} 到 {end_date}")
            return pd.DataFrame()
        
        # 获取表头
        headers_row = table.find('thead')
        if headers_row:
            th_tags = headers_row.find_all('th')
            column_names = [th.get_text(strip=True) for th in th_tags]
        else:
            # 如果没有thead，查找第一行作为表头
            first_row = table.find('tr')
            if first_row:
                th_tags = first_row.find_all(['th', 'td'])
                column_names = [th.get_text(strip=True) for th in th_tags]
            else:
                print("未找到表头")
                return pd.DataFrame()
        
        # 获取数据行
        rows = table.find_all('tr')[1:]  # 跳过表头
        if not rows:
            print(f"没有找到数据行，请求日期范围: {start_date} 到 {end_date}")
            return pd.DataFrame()
            
        all_data = []
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= len(column_names):
                row_data = [cell.get_text(strip=True) for cell in cells[:len(column_names)]]
                all_data.append(row_data)
        
        if not all_data:
            print(f"没有获取到有效数据，请求日期范围: {start_date} 到 {end_date}")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data, columns=column_names if column_names else [
            'Date', 'Contract', 'Open', 'Highest', 'Lowest', 'Close', 
            'Up/Down(yuan)', 'Up/Down(%)', 'Weighted Average Price', 
            'Volume(Kg)', 'Amount(yuan)', 'Open Interest(Lot)', 
            'Direction', 'Delivery Volume (Lot)'
        ])
        
        # 数据类型转换
        numeric_columns = ['Open', 'Highest', 'Lowest', 'Close', 'Up/Down(yuan)', 
                          'Weighted Average Price', 'Volume(Kg)', 'Amount(yuan)', 
                          'Open Interest(Lot)', 'Delivery Volume (Lot)']
        
        percentage_columns = ['Up/Down(%)']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].apply(parse_number)
                
        for col in percentage_columns:
            if col in df.columns:
                df[col] = df[col].apply(parse_percentage)
        
        print(f"已获取数据，日期范围: {start_date} 到 {end_date}，共 {len(df)} 条记录")
        return df
        
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"解析数据时出错: {e}")
        return pd.DataFrame()

def get_all_gold_data():
    """
    获取从10年前或2024年1月1日到今天的全部黄金数据（取较晚的日期作为起始），每次获取半个月
    """
    today = datetime.today().date()
    ten_years_ago = today.replace(year=today.year - 10)
    default_start = datetime(2024, 1, 1).date()
    
    # 取较晚的日期作为起始日期
    start_date_obj = max(ten_years_ago, default_start)
    start_date = start_date_obj
    
    print(f"获取数据时间范围: {start_date} 到 {today}")
    
    all_df = pd.DataFrame()
    
    current_start = start_date
    while current_start <= today:
        # 计算半个月后的日期（大约15天）
        current_end = current_start + timedelta(days=14)
        
        # 如果结束日期超过了今天，则使用今天
        if current_end > today:
            current_end = today
        
        query_start = current_start.strftime('%Y-%m-%d')
        query_end = current_end.strftime('%Y-%m-%d')
        
        print(f"正在获取 {query_start} 到 {query_end} 的数据...")
        
        df = get_gold_data(query_start, query_end)
        
        if not df.empty:
            all_df = pd.concat([all_df, df], ignore_index=True)
        
        # 移动到下一个时间段
        current_start = current_end + timedelta(days=1)
        
        # 添加延迟避免请求过于频繁
        time.sleep(1)
    
    # 按日期升序排序（从最旧到最新）
    if 'Date' in all_df.columns and not all_df.empty:
        # 尝试多种日期格式进行转换
        date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y年%m月%d日']
        date_parsed = False
        
        for fmt in date_formats:
            try:
                all_df['Date_temp'] = pd.to_datetime(all_df['Date'], format=fmt, errors='coerce')
                date_parsed = True
                break
            except ValueError:
                continue
        
        if not date_parsed:
            # 如果无法匹配特定格式，尝试自动推断
            try:
                all_df['Date_temp'] = pd.to_datetime(all_df['Date'], errors='coerce')
                date_parsed = True
            except ValueError:
                pass
        
        if date_parsed:
            # 按日期排序（升序，即从最早的日期到最新的日期）
            all_df = all_df.sort_values(by='Date_temp', ascending=True).drop(columns=['Date_temp'])
    
    return all_df

def add_chinese_headers(df):
    """
    为DataFrame添加中文表头释义
    """
    if df.empty:
        return df
    
    # 定义英文表头与中文释义的映射关系
    header_mapping = {
        'Date': '日期',
        'Contract': '合约',
        'Open': '开盘价',
        'Highest': '最高价',
        'Lowest': '最低价',
        'Close': '收盘价',
        'Up/Down(yuan)': '涨跌(元)',
        'Up/Down(%)': '涨跌(%)',
        'Weighted Average Price': '加权平均价格',
        'Volume(Kg)': '成交量(千克)',
        'Amount(yuan)': '金额(元)',
        'Open Interest(Lot)': '开盘价持仓量(批次)',
        'Direction': '方向',
        'Delivery Volume (Lot)': '交割成交量(批次)'
    }
    
    # 创建新的列名列表，格式为"英文(中文)"
    new_columns = []
    for col in df.columns:
        if col in header_mapping:
            new_col_name = f"{col}({header_mapping[col]})"
        else:
            new_col_name = col  # 如果没有对应中文释义，保持原名称
        new_columns.append(new_col_name)
    
    # 更新DataFrame的列名
    df.columns = new_columns
    
    return df

def format_excel_with_percentages(df, output_path):
    """
    将DataFrame保存到Excel，并设置百分比格式
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='黄金数据', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['黄金数据']
        
        # 找到包含百分比的列并设置格式
        for col_num, col_name in enumerate(df.columns, 1):
            if '(涨跌(%))' in col_name or 'Up/Down(%)' in col_name:
                # openpyxl的列索引从1开始
                for row_num in range(2, len(df) + 2):  # 从第二行开始（第一行是标题）
                    cell = worksheet.cell(row=row_num, column=col_num)
                    if cell.value is not None and cell.value != '':
                        try:
                            # 将小数转为百分比格式（如果还不是百分比格式的话）
                            cell.number_format = '0.00%'
                        except:
                            continue

def main():
    """
    主函数：获取黄金数据并保存到Excel
    """
    print("开始获取黄金(Au99.99)数据...")
    
    # 获取所有数据
    gold_df = get_all_gold_data()
    
    if not gold_df.empty:
        # 添加中文表头释义
        gold_df = add_chinese_headers(gold_df)
        
        # 定义输出路径
        output_path = "/Users/chenzhangjie/Downloads/黄金（Au99.99）.xlsx"
        
        # 保存到Excel并设置百分比格式
        format_excel_with_percentages(gold_df, output_path)
        
        print(f"数据已成功保存到 {output_path}")
        print(f"总共获取了 {len(gold_df)} 条记录")
        print("前几条数据预览:")
        print(gold_df.head())
        
        if 'Date(日期)' in gold_df.columns and len(gold_df) > 0:
            print(f"\n数据时间范围: {gold_df.iloc[0]['Date(日期)']} 到 {gold_df.iloc[-1]['Date(日期)']}")
    else:
        print("未能获取到任何数据")

if __name__ == "__main__":
    main()