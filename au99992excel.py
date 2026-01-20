import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta, date
import time
import re
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retries():
    """创建具有重试策略的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # 总重试次数
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
        allowed_methods=["HEAD", "GET", "OPTIONS"],  # 允许重试的方法
        backoff_factor=1  # 重试间隔
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

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
        session = create_session_with_retries()
        # 设置请求超时
        response = session.get(url, headers=headers, timeout=(10, 30))
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
        
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        return pd.DataFrame()
    except requests.exceptions.Timeout as e:
        print(f"请求超时: {e}")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"解析数据时出错: {e}")
        return pd.DataFrame()

def get_historical_gold_data(start_date_obj, end_date_obj, cookies=None):
    """
    获取指定日期范围内的黄金历史数据
    :param start_date_obj: 开始日期对象
    :param end_date_obj: 结束日期对象
    :param cookies: 可选的cookies
    :return: 包含黄金数据的DataFrame
    """
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
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
    
    all_data = []
    
    page = 1
    should_stop = False  # 是否应该停止翻页
    
    while not should_stop:
        print(f"正在获取历史数据第 {page} 页...")
        
        # 获取当前页面
        page_url = f"https://en.sge.com.cn/data_DailyReport?p={page}"
        
        try:
            session = create_session_with_retries()
            page_response = session.get(page_url, headers=headers, timeout=(10, 30))
            page_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"获取第 {page} 页失败: {e}")
            # 等待稍长时间后重试
            time.sleep(5)
            try:
                page_response = session.get(page_url, headers=headers, timeout=(10, 30))
                page_response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"重试第 {page} 页仍然失败: {e}")
                page += 1
                continue
        
        # 检查是否有内容
        if "没有找到相关记录" in page_response.text or "暂无数据" in page_response.text:
            print(f"第 {page} 页没有数据，停止获取")
            break
        
        page_soup = BeautifulSoup(page_response.text, 'html.parser')
        
        # 修复：查找所有可能的报告列表项（包括带bgColor_tr的行）
        report_items = page_soup.find_all('li', class_=re.compile(r'lh45 border_ea_b'))
        
        if not report_items:
            print(f"第 {page} 页没有找到报告列表，停止获取")
            break
        
        # 检查当前页所有数据是否都在时间范围内
        page_has_valid_data = False  # 当前页是否有有效数据
        
        for item in report_items:
            # 提取日期
            date_span = item.find('span', class_='pull-right')
            if not date_span:
                continue
                
            date_str = date_span.get_text(strip=True)  # 如 "23-12-29"
            
            # 将短日期格式转换为完整日期
            full_date_str = f"20{date_str}"  # "2023-12-29"
            try:
                report_date_obj = datetime.strptime(full_date_str, '%Y-%m-%d').date()
            except ValueError:
                continue  # 日期格式不正确，跳过
            
            # 检查日期是否在目标范围内
            if report_date_obj < start_date_obj:
                # 如果发现日期早于所需范围，停止翻页
                print(f"发现日期 {report_date_obj} 早于所需范围 {start_date_obj}，停止翻页")
                should_stop = True
                break
            elif report_date_obj > end_date_obj:
                # 如果日期超出范围但仍在所需范围内之后，跳过这条数据但继续处理
                continue
            else:
                # 日期在目标范围内，处理数据
                page_has_valid_data = True
                
                # 获取报告链接
                link_tag = item.find('a', href=re.compile(r'/data_DailyReport/\d+'))
                if not link_tag:
                    continue
                    
                href = link_tag.get('href')
                report_url = f"https://en.sge.com.cn{href}"
                
                # 获取具体报告页面的数据
                try:
                    report_response = session.get(report_url, headers=headers, timeout=(10, 30))
                    report_response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    print(f"获取报告页面 {report_url} 失败: {e}")
                    # 等待后重试
                    time.sleep(2)
                    try:
                        report_response = session.get(report_url, headers=headers, timeout=(10, 30))
                        report_response.raise_for_status()
                    except requests.exceptions.RequestException as e:
                        print(f"重试报告页面 {report_url} 仍然失败: {e}")
                        continue
                
                report_soup = BeautifulSoup(report_response.text, 'html.parser')
                
                # 查找表格中的Au99.99数据
                table = report_soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    
                    # 假设第一行为表头
                    if len(rows) > 1:
                        header_row = rows[0]
                        headers_list = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                        
                        # 在后续行中查找Au99.99数据
                        for row in rows[1:]:
                            cells = row.find_all(['td', 'th'])
                            if cells:
                                row_data = [cell.get_text(strip=True) for cell in cells]
                                
                                # 检查是否为Au99.99合约
                                contract_col_idx = -1
                                for i, header in enumerate(headers_list):
                                    if any(keyword in header for keyword in ['Contract', '合约', '商品']):
                                        contract_col_idx = i
                                        break
                                
                                if contract_col_idx != -1 and len(row_data) > contract_col_idx:
                                    contract_value = row_data[contract_col_idx].strip()
                                    
                                    # 只抓取Au99.99的数据，排除iAu9999等其他
                                    if contract_value.upper() == 'AU9999' or contract_value.upper() == 'AU99.99':
                                        
                                        # 添加日期到行数据
                                        row_with_date = [str(report_date_obj)] + row_data if report_date_obj else row_data
                                        # 添加到结果列表
                                        all_data.append(row_with_date)
        
        # 如果没有更多有效数据或者需要停止翻页，则退出循环
        if not page_has_valid_data or should_stop:
            break
        
        # 移动到下一页
        page += 1
        
        # 添加延时以避免请求过于频繁
        time.sleep(1)
    
    # 创建DataFrame
    if all_data:
        # 确定列名 - 添加日期列
        headers_with_date = ['Date'] + headers_list if 'Date' not in headers_list else headers_list
        # 使用第一行数据长度来确定列数
        max_cols = max(len(row) for row in all_data) if all_data else 0
        if len(headers_with_date) < max_cols:
            # 如果表头不够，补充默认列名
            for i in range(len(headers_with_date), max_cols):
                headers_with_date.append(f'Column_{i}')
        
        df = pd.DataFrame(all_data, columns=headers_with_date[:max_cols])
        
        # 应用数据类型转换
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
        
        print(f"已获取 {start_date_obj} 至 {end_date_obj} 历史数据，共 {len(df)} 条记录")
        return df
    else:
        print(f"没有获取到 {start_date_obj} 至 {end_date_obj} 的历史数据")
        return pd.DataFrame()

def get_recent_gold_data(n_years, cookies=None):
    """
    获取近n年的黄金数据
    :param n_years: 年数
    :param cookies: 可选的cookies
    :return: 包含黄金数据的DataFrame
    """
    today = datetime.today().date()
    start_date_obj = max(today.replace(year=today.year - n_years), date(2017, 1, 1))
    
    all_df = pd.DataFrame()
    
    # 判断是否需要获取历史数据（2023年及以前）和当前数据（2024年及以后）
    needs_historical_data = start_date_obj.year <= 2023
    needs_current_data = today.year >= 2024
    
    if needs_historical_data:
        # 获取历史数据（2023年及以前）
        hist_start_date = start_date_obj
        hist_end_date = min(datetime(2023, 12, 31).date(), today)
        if hist_end_date >= hist_start_date:
            print(f"获取 {hist_start_date} 至 {hist_end_date} 历史数据...")
            historical_df = get_historical_gold_data(hist_start_date, hist_end_date, cookies=cookies)
            if not historical_df.empty:
                all_df = pd.concat([all_df, historical_df], ignore_index=True)
    
    if needs_current_data:
        # 获取当前数据（2024年及以后）
        current_start_date = max(datetime(2024, 1, 1).date(), start_date_obj)
        if today >= current_start_date:
            print(f"获取 {current_start_date} 至 {today} 当前数据...")
            current_df = get_all_gold_data_since_2024(current_start_date)
            if not current_df.empty:
                all_df = pd.concat([all_df, current_df], ignore_index=True)
    
    # 按日期升序排序
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
    
    # 对合并后的数据也应用数据类型转换
    numeric_columns = ['Open', 'Highest', 'Lowest', 'Close', 'Up/Down(yuan)', 
                      'Weighted Average Price', 'Volume(Kg)', 'Amount(yuan)', 
                      'Open Interest(Lot)', 'Delivery Volume (Lot)']
    
    percentage_columns = ['Up/Down(%)']
    
    for col in numeric_columns:
        if col in all_df.columns:
            all_df[col] = all_df[col].apply(parse_number)
            
    for col in percentage_columns:
        if col in all_df.columns:
            all_df[col] = all_df[col].apply(parse_percentage)
    
    return all_df

def get_all_gold_data_since_2024(start_date_obj):
    """
    获取从指定起始日期到今天的全部黄金数据，每次获取半个月
    :param start_date_obj: 开始日期对象
    """
    today = datetime.today().date()
    
    print(f"获取数据时间范围: {start_date_obj} 到 {today}")
    
    all_df = pd.DataFrame()
    
    current_start = start_date_obj
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

def main(n_years=5):
    """
    主函数：获取近n年的黄金数据并保存到Excel
    :param n_years: 要获取数据的年数，默认为5年
    """
    print(f"开始获取近{n_years}年的黄金(Au99.99)数据...")
    
    # 获取近n年数据
    gold_df = get_recent_gold_data(n_years=n_years)
    
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
    # 可以在这里指定要获取多少年的数据
    main(n_years=10)