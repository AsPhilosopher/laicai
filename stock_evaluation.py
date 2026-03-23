import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple


# Excel 文件路径配置
EXCEL_FILES = {
    0: "output/股票指数数据.xlsx",
    1: "output/黄金（Au99.99）.xlsx"
}

# 股票指数 sheet 名称配置
STOCK_SHEET_NAMES = {
    0: "上证综合指数",
    1: "深证成分指数",
    2: "创业板指数",
    3: "沪深 300 指数",
    4: "上证 50 指数",
    5: "中证小盘 500 指数",
    6: "中证 1000 指数",
    7: "上证科创板综合指数"
}

DATE_COL = "日期Date"
CLOSE_COL = "收盘Close"


def get_excel_config():
    """
    通过用户输入获取 Excel 文件路径和 Sheet 名称配置
    
    Returns:
        tuple: (excel_path, sheet_name)
    """
    print("\n=== 选择 Excel 文件 ===")
    print("0 = output/股票指数数据.xlsx")
    print("1 = output/黄金（Au99.99）.xlsx")
    
    while True:
        try:
            file_choice = int(input("请选择 Excel 文件 (输入 0 或 1): "))
            if file_choice not in EXCEL_FILES.keys():
                print("无效输入，请输入 0 或 1")
                continue
            break
        except ValueError:
            print("无效输入，请输入数字 0 或 1")
    
    excel_path = EXCEL_FILES[file_choice]
    
    # 如果选择的是黄金文件，直接使用默认的 sheet 名称
    if file_choice == 1:
        sheet_name = "黄金数据"
        print(f"\n已选择：{excel_path}")
        print(f"Sheet 名称：{sheet_name}")
    else:
        # 如果选择的是股票指数文件，让用户选择 sheet
        print("\n=== 选择 Sheet ===")
        for idx, name in STOCK_SHEET_NAMES.items():
            print(f"{idx} = {name}")
        
        while True:
            try:
                sheet_choice = int(input("请选择 Sheet (输入 0-7): "))
                if sheet_choice not in STOCK_SHEET_NAMES.keys():
                    print("无效输入，请输入 0-7 之间的数字")
                    continue
                break
            except ValueError:
                print("无效输入，请输入 0-7 之间的数字")
        
        sheet_name = STOCK_SHEET_NAMES[sheet_choice]
        print(f"\n已选择：{excel_path}")
        print(f"Sheet 名称：{sheet_name}")
    
    return excel_path, sheet_name


def load_excel_data(excel_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    读取 Excel 数据，返回按日期升序排序后的 DataFrame
    
    参数:
        excel_path: Excel 文件路径
        sheet_name: Sheet 名称（可选，如为 None 则读取第一个 Sheet）
        
    返回:
        pd.DataFrame: 包含日期和收盘价的数据框，已按日期升序排序
    """
    try:
        if sheet_name:
            df = pd.read_excel(
                excel_path,
                sheet_name=sheet_name,
                engine="openpyxl",
                dtype=str,
            )
        else:
            df = pd.read_excel(
                excel_path,
                sheet_name=0,
                engine="openpyxl",
                dtype=str,
            )
    except Exception as e:
        raise ValueError(f"读取 Excel 文件失败：{str(e)}")
    
    # 兼容日期列名差异
    possible_date_cols = [DATE_COL, "日期", "Date", "Date(日期)"]
    found_date_col = None
    for col in possible_date_cols:
        if col in df.columns:
            found_date_col = col
            break
    if found_date_col is None:
        raise ValueError(
            f"Excel 中未找到日期列，已支持的列名包括：{', '.join(possible_date_cols)}"
        )
    
    # 统一重命名日期列
    if found_date_col != DATE_COL:
        df = df.rename(columns={found_date_col: DATE_COL})
    
    # 兼容不同收盘价列名差异
    possible_close_cols = [CLOSE_COL, "收盘价", "Close", "Close(收盘价)"]
    found_close_col = None
    for col in possible_close_cols:
        if col in df.columns:
            found_close_col = col
            break
    if found_close_col is None:
        raise ValueError(
            f"Excel 中未找到收盘价列，已支持的列名包括：{', '.join(possible_close_cols)}"
        )
    
    # 统一重命名收盘价列
    if found_close_col != CLOSE_COL:
        df = df.rename(columns={found_close_col: CLOSE_COL})
    
    df = df.copy()
    
    # 统一解析日期
    date_series = df[DATE_COL].astype(str)
    parsed_dates = pd.to_datetime(date_series, format="%Y%m%d", errors="coerce")
    mask_na = parsed_dates.isna()
    if mask_na.any():
        parsed_dates2 = pd.to_datetime(
            date_series[mask_na], format="%Y-%m-%d", errors="coerce"
        )
        parsed_dates.loc[mask_na] = parsed_dates2
    
    # 过滤无效日期
    invalid_mask = parsed_dates.isna()
    if invalid_mask.any():
        valid_mask = ~invalid_mask
        df = df.loc[valid_mask].reset_index(drop=True)
        parsed_dates = parsed_dates.loc[valid_mask].reset_index(drop=True)
    
    df[DATE_COL] = parsed_dates
    df = df.sort_values(DATE_COL).reset_index(drop=True)
    
    return df


def calculate_close_price_percentile(
    df: pd.DataFrame,
    close_price: float,
    years: int = 5,
    as_of_date: Optional[datetime] = None,
) -> dict:
    """
    计算给定收盘价在最近 N 年中的百分位排名
    
    参数:
        df: 包含日期和收盘价的数据框
        close_price: 要计算的收盘价
        years: 向前回溯的年数（默认 10 年）
        as_of_date: 截止日期（默认使用数据中最新的日期）
        
    返回:
        dict 包含:
            - close_price: 输入的收盘价
            - percentile_rank: 百分位排名 (0-100)，表示超过百分之多少的数据
            - years: 回溯年数
            - window_size: 窗口内的数据点数
            - min_close: 窗口内最低收盘价
            - max_close: 窗口内最高收盘价
            - avg_close: 窗口内平均收盘价
            - description: 描述性文字
            
    说明:
        - 如果收盘价高于 N 年内所有价格，percentile_rank > 100
        - 如果收盘价低于 N 年内所有价格，percentile_rank < 0
        - 否则返回 0-100 之间的值，表示超过百分之多少的数据
    """
    # 确定截止日期
    if as_of_date is None:
        as_of_date = df[DATE_COL].max().to_pydatetime()
    
    as_of_ts = pd.to_datetime(as_of_date)
    window_start = as_of_ts - timedelta(days=years * 365)
    
    # 获取时间窗口内的数据
    window_df = df[(df[DATE_COL] >= window_start) & (df[DATE_COL] <= as_of_ts)]
    
    if window_df.empty:
        raise ValueError("所选时间窗口内没有历史数据，无法计算百分位排名。")
    
    closes = window_df[CLOSE_COL].astype(float)
    window_size = len(closes)
    
    # 计算百分位排名
    below_count = (closes < close_price).sum()
    equal_count = (closes == close_price).sum()
    
    # 使用线性插值法计算百分位排名
    percentile_rank = (below_count + 0.5 * equal_count) / window_size * 100
    
    # 获取窗口内的统计信息
    min_close = closes.min()
    max_close = closes.max()
    avg_close = closes.mean()
    
    # 处理边界情况
    if close_price > max_close:
        # 高于最大值，计算超出比例
        excess_pct = (close_price - max_close) / max_close * 100
        percentile_rank = 100.0 + excess_pct
    elif close_price < min_close:
        # 低于最小值，计算低于比例
        deficit_pct = (min_close - close_price) / min_close * 100
        percentile_rank = 0.0 - deficit_pct
    
    # 生成描述性文字
    if percentile_rank > 100:
        description = f"收盘价 {close_price:.2f} 高于近{years}年所有价格，超出{(percentile_rank-100):.1f}%"
    elif percentile_rank < 0:
        description = f"收盘价 {close_price:.2f} 低于近{years}年所有价格，低于{abs(percentile_rank):.1f}%"
    else:
        description = f"收盘价 {close_price:.2f} 高于近{years}年{percentile_rank:.1f}%的价格水平"
    
    return {
        "close_price": close_price,
        "percentile_rank": percentile_rank,
        "years": years,
        "window_size": window_size,
        "min_close": min_close,
        "max_close": max_close,
        "avg_close": avg_close,
        "description": description,
    }


def main():
    """
    主函数：交互式输入参数并计算收盘价百分位排名
    """
    print("=== 收盘价百分位排名计算工具 ===")
    
    # 获取配置（与 stock_purchase_strategy.py 一致）
    excel_path, sheet_name = get_excel_config()
    
    # 加载数据
    try:
        print(f"\n正在加载数据：{excel_path}")
        print(f"Sheet: {sheet_name}")
        df = load_excel_data(excel_path, sheet_name)
        print(f"成功加载 {len(df)} 条数据")
        print(f"数据日期范围：{df[DATE_COL].min().strftime('%Y-%m-%d')} 至 {df[DATE_COL].max().strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"错误：{e}")
        return
    
    # 获取计算参数
    print("\n=== 计算参数 ===")
    close_price_str = input("请输入收盘价 C: ").strip()
    try:
        close_price = float(close_price_str)
    except ValueError:
        print("错误：收盘价必须是数字")
        return
    
    years_str = input("请输入回溯年数 N（默认 10）: ").strip() or "10"
    try:
        years = int(years_str)
        if years <= 0:
            print("错误：年数必须为正整数")
            return
    except ValueError:
        print("错误：年数必须为整数")
        return
    
    # 可选：指定截止日期
    default_date = df[DATE_COL].max().strftime("%Y-%m-%d")
    date_str = input(f"请输入截止日期 YYYY-MM-DD（默认 {default_date}）: ").strip()
    if date_str:
        try:
            as_of_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("错误：日期格式不正确")
            return
    else:
        as_of_date = None
    
    # 计算百分位排名
    try:
        result = calculate_close_price_percentile(
            df=df,
            close_price=close_price,
            years=years,
            as_of_date=as_of_date,
        )
        
        # 输出结果
        print("\n" + "=" * 40)
        print("计算结果")
        print("=" * 40)
        print(f"收盘价：{result['close_price']:.2f}")
        print(f"回溯年数：{result['years']}年")
        print(f"样本数量：{result['window_size']}个交易日")
        print(f"最低收盘价：{result['min_close']:.2f}")
        print(f"最高收盘价：{result['max_close']:.2f}")
        print(f"平均收盘价：{result['avg_close']:.2f}")
        print(f"\n百分位排名：{result['percentile_rank']:.1f}%")
        print(f"说明：{result['description']}")
        print("=" * 40)
        
    except Exception as e:
        print(f"错误：{e}")


if __name__ == "__main__":
    main()
