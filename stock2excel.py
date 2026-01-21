import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
import tempfile


# 指数代码和名称映射
INDEX_MAP = {
    "000001": "上证综合指数",
    "000300": "沪深300指数",
    "000016": "上证50指数",
    "000905": "中证小盘500指数",
    "000852": "中证1000指数",
    "000680": "上证科创板综合指数",
    "399001": "深证成分指数",  # 新增：深证成指
    "399006": "创业板指数"   # 新增：创业板指
}


def get_date_range(years: int = 10) -> Tuple[str, str]:
    """
    获取近N年的日期范围
    返回格式: (startDate, endDate) 格式为 YYYYMMDD
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    start_date_str = start_date.strftime("%Y%m%d")
    end_date_str = end_date.strftime("%Y%m%d")
    
    return start_date_str, end_date_str


def convert_date_format(date_str: str) -> str:
    """
    将YYYYMMDD格式转换为YYYY-MM-DD格式
    """
    if len(date_str) != 8:
        raise ValueError("日期格式不正确，应为YYYYMMDD")
    
    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]
    
    return f"{year}-{month}-{day}"


def download_index_data(index_code: str, start_date: str, end_date: str) -> bytes:
    """
    下载指定指数的Excel数据
    
    Args:
        index_code: 指数代码
        start_date: 开始日期 (YYYYMMDD格式)
        end_date: 结束日期 (YYYYMMDD格式)
    
    Returns:
        Excel文件的二进制数据
    """
    # 判断是否为新的API支持的指数（399001或399006）
    if index_code in ["399001", "399006"]:
        # 使用新的API端点
        url = "https://hq.cnindex.com.cn/market/market/downloadDailyMarketExcel"
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.cnindex.com.cn',
            'Referer': 'https://www.cnindex.com.cn/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="135", "Not-A.Brand";v="8"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        
        # 转换日期格式
        start_date_formatted = convert_date_format(start_date)
        end_date_formatted = convert_date_format(end_date)
        
        # 构建请求数据
        data = f"indexCode={index_code}&startDate={start_date_formatted}&endDate={end_date_formatted}&frequency=day"
        
        try:
            print(f"正在下载 {INDEX_MAP.get(index_code, index_code)} ({index_code}) 的数据...")
            response = requests.post(
                url,
                headers=headers,
                data=data,
                cookies={'language': 'zh_CN', 'fileDownload': 'true'},
                timeout=60
            )
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower() or response.content.startswith(b'PK'):
                return response.content
            else:
                print(f"响应内容: {response.text[:200]}")
                raise Exception(f"响应不是Excel文件，Content-Type: {content_type}")
                
        except requests.exceptions.RequestException as e:
            print(f"下载 {index_code} 数据失败: {e}")
            raise
    else:
        # 使用原来的API端点
        url = "https://www.csindex.com.cn/csindex-home/exportExcel/downloadindex-perf"
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://www.csindex.com.cn',
            'Referer': 'https://www.csindex.com.cn/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        
        # 构建请求数据
        data = [{
            "startDate": start_date,
            "endDate": end_date,
            "indexCode": index_code
        }]
        
        try:
            print(f"正在下载 {INDEX_MAP.get(index_code, index_code)} ({index_code}) 的数据...")
            response = requests.post(
                url,
                headers=headers,
                json=data,
                params={"language": "CH"},
                timeout=60
            )
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'excel' in content_type.lower() or 'spreadsheet' in content_type.lower() or response.content.startswith(b'PK'):
                return response.content
            else:
                # 如果不是Excel文件，尝试解析为JSON查看错误信息
                try:
                    error_info = response.json()
                    print(f"错误: {error_info}")
                except:
                    print(f"响应内容: {response.text[:200]}")
                raise Exception(f"响应不是Excel文件，Content-Type: {content_type}")
                
        except requests.exceptions.RequestException as e:
            print(f"下载 {index_code} 数据失败: {e}")
            raise


def read_excel_from_bytes(excel_bytes: bytes) -> pd.DataFrame:
    """
    从二进制数据读取Excel文件
    
    Args:
        excel_bytes: Excel文件的二进制数据
    
    Returns:
        DataFrame对象
    """
    try:
        # 使用临时文件来读取Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(excel_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            # 读取Excel文件
            df = pd.read_excel(tmp_file_path, engine='openpyxl')
            return df
        finally:
            # 删除临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    except Exception as e:
        print(f"读取Excel数据失败: {e}")
        raise


def export_all_indices_to_excel(output_file: str = None, years: int = 10):
    """
    导出所有指数数据到一个Excel文件，每个指数一个sheet
    
    Args:
        output_file: 输出文件路径，如果为None则使用默认路径
        years: 获取近N年的数据，默认10年
    """
    if output_file is None:
        output_file = "output/股票指数数据.xlsx"

    # 确保output文件夹存在
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取日期范围
    start_date, end_date = get_date_range(years)
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"共 {len(INDEX_MAP)} 个指数需要下载\n")
    
    # 存储所有指数的数据
    all_data: Dict[str, pd.DataFrame] = {}
    
    # 遍历每个指数代码
    for index_code, index_name in INDEX_MAP.items():
        try:
            # 下载数据
            excel_bytes = download_index_data(index_code, start_date, end_date)
            
            # 读取Excel数据
            df = read_excel_from_bytes(excel_bytes)
            
            if df.empty:
                print(f"警告: {index_name} ({index_code}) 的数据为空")
                continue
            
            # 添加指数代码和名称列（如果需要）
            df.insert(0, '指数代码', index_code)
            df.insert(1, '指数名称', index_name)
            
            # 使用指数名称作为sheet名称（Excel sheet名称有长度限制）
            sheet_name = index_name[:31]  # Excel sheet名称最多31个字符
            
            all_data[sheet_name] = df
            print(f"✓ {index_name} ({index_code}): 获取到 {len(df)} 条记录\n")
            
        except Exception as e:
            print(f"✗ {index_name} ({index_code}) 处理失败: {e}\n")
            continue
    
    # 将所有数据写入Excel文件
    if not all_data:
        print("没有获取到任何数据，无法生成Excel文件")
        return
    
    print(f"正在保存到Excel文件: {output_file}")
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for sheet_name, df in all_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"\n✓ 所有数据已成功保存到: {output_file}")
        print(f"共 {len(all_data)} 个指数数据表")
        for sheet_name, df in all_data.items():
            print(f"  - {sheet_name}: {len(df)} 条记录")
    except Exception as e:
        print(f"保存Excel文件失败: {e}")
        raise

def main(n_years=5):
    """
    主函数，用于测试
    """
    export_all_indices_to_excel(years=n_years)
    print("\n所有数据导出完成！")

if __name__ == "__main__":
    main(n_years=10)