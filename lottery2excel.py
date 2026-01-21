import requests
import json
import pandas as pd
import os
from typing import List, Dict, Any


def get_ssq_data() -> List[Dict[str, Any]]:
    """获取双色球数据"""
    url = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    params = {
        "name": "ssq",
        "issueCount": "",
        "issueStart": "",
        "issueEnd": "",
        "dayStart": "",
        "dayEnd": "",
        "pageNo": 1,
        "pageSize": 300000,
        "week": "",
        "systemType": "PC"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("state") == 0 and data.get("result"):
            return data["result"]
        else:
            print(f"双色球API返回异常: {data.get('message', '未知错误')}")
            return []
    except Exception as e:
        print(f"获取双色球数据失败: {e}")
        return []


def get_dlt_data() -> List[Dict[str, Any]]:
    """获取大乐透数据（支持翻页获取全部数据）"""
    url = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.lottery.gov.cn/",
        "Origin": "https://www.lottery.gov.cn",
        "Connection": "keep-alive"
    }
    
    try:
        # 使用Session来保持连接
        session = requests.Session()
        all_data = []
        
        # 先获取第一页数据，获取总数
        params_first = {
            "gameNo": "85",
            "provinceId": "0",
            "pageSize": 100,  # 每页最多100条
            "isVerify": "1",
            "pageNo": "1"
        }
        
        print("正在获取第1页数据...")
        response = session.get(url, params=params_first, headers=headers, timeout=30)
        response.raise_for_status()
        first_data = response.json()
        
        if not first_data.get("value"):
            print(f"大乐透API返回异常: {first_data.get('message', '未知错误')}")
            return []
        
        value = first_data["value"]
        total = value.get("total", 0)  # 获取总数据量
        first_list = value.get("list", [])
        
        if not first_list:
            print("未获取到大乐透数据")
            return []
        
        all_data.extend(first_list)
        print(f"第1页: 获取到 {len(first_list)} 条数据，总计 {len(all_data)}/{total} 条")
        
        # 计算总页数
        page_size = 100
        total_pages = (total + page_size - 1) // page_size  # 向上取整
        
        # 如果只有一页，直接返回
        if total_pages <= 1:
            return all_data
        
        # 翻页获取剩余数据
        for page_no in range(2, total_pages + 1):
            params_page = {
                "gameNo": "85",
                "provinceId": "0",
                "pageSize": page_size,
                "isVerify": "1",
                "pageNo": str(page_no)
            }
            
            print(f"正在获取第{page_no}页数据...")
            response = session.get(url, params=params_page, headers=headers, timeout=30)
            response.raise_for_status()
            page_data = response.json()
            
            if page_data.get("value") and page_data["value"].get("list"):
                page_list = page_data["value"]["list"]
                all_data.extend(page_list)
                print(f"第{page_no}页: 获取到 {len(page_list)} 条数据，总计 {len(all_data)}/{total} 条")
            else:
                print(f"第{page_no}页: 未获取到数据")
                break
        
        print(f"\n大乐透数据获取完成，共获取 {len(all_data)} 条数据（总计 {total} 条）")
        return all_data
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
        if 'response' in locals():
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
        return []
    except Exception as e:
        print(f"获取大乐透数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def process_ssq_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """处理双色球数据并转换为DataFrame"""
    rows = []
    
    for item in data:
        # 解析红球号码（前6个）
        red_balls = []
        if item.get("red"):
            red_balls = item["red"].split(",")
            # 确保有6个号码，不足的用空字符串填充
            while len(red_balls) < 6:
                red_balls.append("")
        
        # 蓝球号码（最后一个）
        blue_ball = item.get("blue", "")
        
        # 销售额和奖池金额转换为整数（先去掉逗号等无用字符）
        sales = item.get("sales", "")
        try:
            if sales:
                # 去掉逗号、空格等无用字符
                sales_clean = str(sales).replace(",", "").replace(" ", "").strip()
                sales_float = float(sales_clean) if sales_clean else 0
            else:
                sales_float = 0
        except (ValueError, TypeError):
            sales_float = 0
        
        poolmoney = item.get("poolmoney", "")
        try:
            if poolmoney:
                # 去掉逗号、空格等无用字符
                poolmoney_clean = str(poolmoney).replace(",", "").replace(" ", "").strip()
                poolmoney_float = float(poolmoney_clean) if poolmoney_clean else 0
            else:
                poolmoney_float = 0
        except (ValueError, TypeError):
            poolmoney_float = 0
        
        row = {
            "期号": item.get("code", ""),
            "红球1": red_balls[0] if len(red_balls) > 0 else "",
            "红球2": red_balls[1] if len(red_balls) > 1 else "",
            "红球3": red_balls[2] if len(red_balls) > 2 else "",
            "红球4": red_balls[3] if len(red_balls) > 3 else "",
            "红球5": red_balls[4] if len(red_balls) > 4 else "",
            "红球6": red_balls[5] if len(red_balls) > 5 else "",
            "蓝球": blue_ball,
            "开奖日期": item.get("date", ""),
            "销售额": sales_float,
            "奖池金额": poolmoney_float,
            "中奖信息": item.get("content", "")
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


def process_dlt_data(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """处理大乐透数据并转换为DataFrame"""
    rows = []
    
    for item in data:
        # 解析号码（7个号码，前5个前区，后2个后区）
        numbers = []
        if item.get("lotteryDrawResult"):
            numbers = item["lotteryDrawResult"].split(" ")
            # 确保有7个号码，不足的用空字符串填充
            while len(numbers) < 7:
                numbers.append("")
        
        # 销售额和奖池金额转换为整数（先去掉逗号等无用字符）
        total_sale = item.get("totalSaleAmount", "")
        try:
            if total_sale:
                # 去掉逗号、空格等无用字符
                total_sale_clean = str(total_sale).replace(",", "").replace(" ", "").strip()
                total_sale_float = float(total_sale_clean) if total_sale_clean else 0
            else:
                total_sale_float = 0
        except (ValueError, TypeError):
            total_sale_float = 0
        
        pool_balance = item.get("poolBalanceAfterdraw", "")
        try:
            if pool_balance:
                # 去掉逗号、空格等无用字符
                pool_balance_clean = str(pool_balance).replace(",", "").replace(" ", "").strip()
                pool_balance_float = float(pool_balance_clean) if pool_balance_clean else 0
            else:
                pool_balance_float = 0
        except (ValueError, TypeError):
            pool_balance_float = 0
        
        row = {
            "期号": item.get("lotteryDrawNum", ""),
            "前区1": numbers[0] if len(numbers) > 0 else "",
            "前区2": numbers[1] if len(numbers) > 1 else "",
            "前区3": numbers[2] if len(numbers) > 2 else "",
            "前区4": numbers[3] if len(numbers) > 3 else "",
            "前区5": numbers[4] if len(numbers) > 4 else "",
            "后区1": numbers[5] if len(numbers) > 5 else "",
            "后区2": numbers[6] if len(numbers) > 6 else "",
            "开奖日期": item.get("lotteryDrawTime", ""),
            "销售额": total_sale_float,
            "奖池金额": pool_balance_float
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


def export_ssq_to_excel():
    """导出双色球数据到Excel"""
    print("正在获取双色球数据...")
    data = get_ssq_data()
    
    if not data:
        print("未获取到双色球数据")
        return
    
    print(f"获取到 {len(data)} 条双色球数据")
    print("正在处理数据...")
    df = process_ssq_data(data)
    
    # 确保output文件夹存在
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    print("正在保存到Excel...")
    excel_path = os.path.join(output_dir, "双色球.xlsx")
    df.to_excel(excel_path, index=False, engine='openpyxl')
    print(f"双色球数据已保存到 {excel_path}，共 {len(df)} 条记录")


def export_dlt_to_excel():
    """导出大乐透数据到Excel"""
    print("正在获取大乐透数据...")
    data = get_dlt_data()
    
    if not data:
        print("未获取到大乐透数据")
        return
    
    print(f"获取到 {len(data)} 条大乐透数据")
    print("正在处理数据...")
    df = process_dlt_data(data)
    
    # 确保output文件夹存在
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    print("正在保存到Excel...")
    excel_path = os.path.join(output_dir, "大乐透.xlsx")
    df.to_excel(excel_path, index=False, engine='openpyxl')
    print(f"大乐透数据已保存到 {excel_path}，共 {len(df)} 条记录")


def export_all_to_excel():
    """将双色球和大乐透数据导出到同一个Excel文件的不同sheet中"""
    # 确保output文件夹存在
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    excel_path = os.path.join(output_dir, "彩票数据（双色球、大乐透）.xlsx")
    
    # 获取并处理双色球数据
    print("正在获取双色球数据...")
    ssq_data = get_ssq_data()
    if not ssq_data:
        print("未获取到双色球数据")
        ssq_df = None
    else:
        print(f"获取到 {len(ssq_data)} 条双色球数据")
        print("正在处理双色球数据...")
        ssq_df = process_ssq_data(ssq_data)
        print(f"双色球数据处理完成，共 {len(ssq_df)} 条记录")
    
    print("\n" + "="*50 + "\n")
    
    # 获取并处理大乐透数据
    print("正在获取大乐透数据...")
    dlt_data = get_dlt_data()
    if not dlt_data:
        print("未获取到大乐透数据")
        dlt_df = None
    else:
        print(f"获取到 {len(dlt_data)} 条大乐透数据")
        print("正在处理大乐透数据...")
        dlt_df = process_dlt_data(dlt_data)
        print(f"大乐透数据处理完成，共 {len(dlt_df)} 条记录")
    
    # 使用ExcelWriter写入多个sheet
    print("\n正在保存到Excel...")
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        if ssq_df is not None:
            ssq_df.to_excel(writer, sheet_name='双色球', index=False)
            print(f"双色球数据已写入sheet: 双色球")
        
        if dlt_df is not None:
            dlt_df.to_excel(writer, sheet_name='大乐透', index=False)
            print(f"大乐透数据已写入sheet: 大乐透")
    
    print(f"\n所有数据已保存到 {excel_path}")
    if ssq_df is not None:
        print(f"  - 双色球: {len(ssq_df)} 条记录")
    if dlt_df is not None:
        print(f"  - 大乐透: {len(dlt_df)} 条记录")


if __name__ == "__main__":
    # 导出所有数据到同一个Excel文件的不同sheet
    export_all_to_excel()
    print("\n所有数据导出完成！")
