import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Tuple


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


# 获取配置
EXCEL_PATH, SHEET_NAME = get_excel_config()

DATE_COL = "日期Date"
CLOSE_COL = "收盘Close"


@dataclass
class DailySignal:
    trade_date: datetime
    close: float
    low_threshold: float
    high_threshold: float
    action: str  # "BUY", "SELL", "HOLD"
    reason: str
    low_threshold_date: Optional[datetime] = None
    high_threshold_date: Optional[datetime] = None


@dataclass
class TradeRecord:
    cycle_id: int
    date: datetime
    action: str  # "BUY", "BUY_ADD", "SELL"
    price: float
    amount: float
    shares: float
    reason: str
    low_threshold: Optional[float] = None  # 买入时的低位阈值
    high_threshold: Optional[float] = None  # 卖出时的高位阈值
    cycle_return: Optional[float] = None  # 卖出时的周期收益率
    cycle_days: Optional[int] = None  # 卖出时该买卖周期经历的天数


def load_index_data(
    excel_path: str = EXCEL_PATH,
    sheet_name: str = SHEET_NAME,
) -> pd.DataFrame:
    """
    读取上证综合指数数据，返回按日期升序排序后的DataFrame
    必含列：日期Date(形如20160302)、收盘Close
    """
    # 先将日期列按字符串读入，再按 YYYYMMDD 解析，避免被错误当成时间戳纳秒
    # 先不强制指定具体列名，统一按字符串读入，方便后续兼容不同表头
    # 若指定的 sheet_name 在文件中不存在（例如黄金 Au99.99 文件只有一个 sheet），
    # 则自动退回读取第一个 sheet，提升兼容性。
    try:
        df = pd.read_excel(
            excel_path,
            sheet_name=sheet_name,
            engine="openpyxl",
            dtype=str,
        )
    except ValueError:
        # 回退为读取第一个 sheet（索引 0）
        df = pd.read_excel(
            excel_path,
            sheet_name=0,
            engine="openpyxl",
            dtype=str,
        )

    # 兼容日期列名差异：
    # - 旧表：日期Date，格式形如 20160302
    # - 新表（股票）：日期，格式形如 2016-03-02
    # - 新表（黄金 Au99.99）：Date 或 Date(日期)
    possible_date_cols = [DATE_COL, "日期", "Date", "Date(日期)"]
    found_date_col = None
    for col in possible_date_cols:
        if col in df.columns:
            found_date_col = col
            break
    if found_date_col is None:
        raise ValueError(
            f"Excel中未找到日期列，已支持的列名包括：{', '.join(possible_date_cols)}"
        )

    # 将实际存在的日期列统一重命名为 DATE_COL
    if found_date_col != DATE_COL:
        df = df.rename(columns={found_date_col: DATE_COL})

    # 兼容不同Sheet中“收盘价”列名差异：
    # - 上证综合指数使用：收盘Close
    # - 深证成分指数、创业板指数使用：收盘价
    # - 黄金 Au99.99 使用：Close 或 Close(收盘价)
    possible_close_cols = [CLOSE_COL, "收盘价", "Close", "Close(收盘价)"]
    found_close_col = None
    for col in possible_close_cols:
        if col in df.columns:
            found_close_col = col
            break
    if found_close_col is None:
        raise ValueError(
            f"Excel中未找到收盘价列，已支持的列名包括：{', '.join(possible_close_cols)}"
        )

    # 将实际存在的收盘价列统一重命名为 CLOSE_COL，方便后续逻辑统一处理
    if found_close_col != CLOSE_COL:
        df = df.rename(columns={found_close_col: CLOSE_COL})

    df = df.copy()

    # 统一解析日期，兼容 "YYYYMMDD" 和 "YYYY-MM-DD" 两种字符串格式
    date_series = df[DATE_COL].astype(str)
    # 先尝试旧格式 YYYYMMDD
    parsed_dates = pd.to_datetime(date_series, format="%Y%m%d", errors="coerce")
    # 对于未能解析的，再尝试新格式 YYYY-MM-DD
    mask_na = parsed_dates.isna()
    if mask_na.any():
        parsed_dates2 = pd.to_datetime(
            date_series[mask_na], format="%Y-%m-%d", errors="coerce"
        )
        parsed_dates.loc[mask_na] = parsed_dates2

    # 对于仍然无法解析的日期行，视为异常数据，直接丢弃
    invalid_mask = parsed_dates.isna()
    if invalid_mask.any():
        # 只保留日期有效的行
        valid_mask = ~invalid_mask
        df = df.loc[valid_mask].reset_index(drop=True)
        parsed_dates = parsed_dates.loc[valid_mask].reset_index(drop=True)

    df[DATE_COL] = parsed_dates
    df = df.sort_values(DATE_COL).reset_index(drop=True)

    return df


def get_nearest_trading_date(
    df: pd.DataFrame,
    target_date: datetime,
    direction: str = "backward",
) -> Optional[pd.Timestamp]:
    """
    获取离目标日期最近的交易日
    direction:
        - backward: 向前找 <= target_date 的最近交易日
        - forward:  向后找 >= target_date 的最近交易日
    """
    dates = df[DATE_COL]
    if direction == "backward":
        mask = dates <= target_date
        if not mask.any():
            return None
        return dates[mask].max()
    else:
        mask = dates >= target_date
        if not mask.any():
            return None
        return dates[mask].min()


def compute_thresholds(
    df: pd.DataFrame,
    as_of_date: datetime,
    years: int = 5,
    low_percent: float = 30.0,
    high_top_percent: float = 20.0,
) -> Tuple[float, float, float, pd.Timestamp, pd.Timestamp]:
    """
    计算指定日期之前N年内的低位x%和高位y%阈值

    low_percent: 底部区间百分比，例如30表示“最低的30%”
    high_top_percent: 最高区间的比例，例如20表示“最高的20%”（即80分位）
    返回：
        - 当前收盘价 current_close
        - 低位阈值价格（使用最接近分位点的那天实际收盘价）low_threshold
        - 高位阈值价格（使用最接近分位点的那天实际收盘价）high_threshold
        - 低位阈值对应日期 low_ref_date
        - 高位阈值对应日期 high_ref_date
    """
    as_of_ts = pd.to_datetime(as_of_date)
    window_start = as_of_ts - timedelta(days=years * 365)

    window_df = df[(df[DATE_COL] > window_start) & (df[DATE_COL] <= as_of_ts)]
    if window_df.empty:
        raise ValueError("所选时间窗口内没有历史数据，无法计算百分位阈值。")

    closes = window_df[CLOSE_COL].astype(float)

    # 例如：最低的30% → 30%分位（先得到理论分位值，再在真实数据中找最接近的一天）
    low_q = float(closes.quantile(low_percent / 100.0))
    # 最高的20% → 顶部20% 对应 1 - 0.2 = 0.8 分位
    high_q = float(closes.quantile(1.0 - high_top_percent / 100.0))

    # 找到当日收盘价
    today_row = df[df[DATE_COL] == as_of_ts]
    if today_row.empty:
        raise ValueError("指定日期不在交易日内，且未做最近交易日对齐。")
    current_close = float(today_row.iloc[0][CLOSE_COL])

    # 仅保留与阈值计算相关的列
    window_df = window_df[[DATE_COL, CLOSE_COL]].copy()

    # 在窗口数据中找到最接近低位/高位“理论分位值”的真实日期和价格
    closes_window = window_df[CLOSE_COL].astype(float)

    low_diff = (closes_window - low_q).abs()
    low_idx = low_diff.idxmin()
    low_ref_date = window_df.loc[low_idx, DATE_COL]
    low_threshold = float(window_df.loc[low_idx, CLOSE_COL])

    high_diff = (closes_window - high_q).abs()
    high_idx = high_diff.idxmin()
    high_ref_date = window_df.loc[high_idx, DATE_COL]
    high_threshold = float(window_df.loc[high_idx, CLOSE_COL])

    return current_close, low_threshold, high_threshold, low_ref_date, high_ref_date


def compute_percentile_rank(
    df: pd.DataFrame,
    as_of_date: datetime,
    years: int = 5,
) -> Tuple[float, float, int]:
    """
    计算指定日期的收盘价在过去 N 年收盘价数据中的百分位排名
    
    参数:
        df: 包含日期和收盘价的数据框
        as_of_date: 指定的日期
        years: 向前回溯的年数
        
    返回:
        - percentile_rank: 百分位排名 (0-100)，如 75.5 表示高于 75.5% 的数据
        - current_close: 当前收盘价
        - window_size: 窗口内的数据点数
        
    说明:
        - 如果收盘价高于 N 年内所有价格，返回 >100
        - 如果收盘价低于 N 年内所有价格，返回 <0
        - 否则返回 0-100 之间的值，表示超过百分之多少的数据
    """
    as_of_ts = pd.to_datetime(as_of_date)
    window_start = as_of_ts - timedelta(days=years * 365)
    
    # 获取时间窗口内的数据
    window_df = df[(df[DATE_COL] >= window_start) & (df[DATE_COL] <= as_of_ts)]
    
    if window_df.empty:
        raise ValueError("所选时间窗口内没有历史数据，无法计算百分位排名。")
    
    closes = window_df[CLOSE_COL].astype(float)
    window_size = len(closes)
    
    # 获取当日收盘价
    today_row = df[df[DATE_COL] == as_of_ts]
    if today_row.empty:
        # 如果指定日期不是交易日，尝试向前找最近的交易日
        trading_date = get_nearest_trading_date(df, as_of_date, direction="backward")
        if trading_date is None:
            raise ValueError("数据中不存在早于该日期的交易日。")
        today_row = df[df[DATE_COL] == trading_date]
        if today_row.empty:
            raise ValueError("无法找到对应的交易日数据。")
    
    current_close = float(today_row.iloc[0][CLOSE_COL])
    
    # 计算百分位排名
    # 方法：统计有多少比例的数据小于当前价格
    below_count = (closes < current_close).sum()
    equal_count = (closes == current_close).sum()
    
    # 使用线性插值法计算百分位排名
    # percentile_rank = (小于当前值的数量 + 0.5 * 等于当前值的数量) / 总数量 * 100
    percentile_rank = (below_count + 0.5 * equal_count) / window_size * 100
    
    # 处理边界情况
    if current_close > closes.max():
        # 高于最大值，计算超出比例
        max_close = closes.max()
        excess_pct = (current_close - max_close) / max_close * 100
        percentile_rank = 100.0 + excess_pct
    elif current_close < closes.min():
        # 低于最小值，计算低于比例
        min_close = closes.min()
        deficit_pct = (min_close - current_close) / min_close * 100
        percentile_rank = 0.0 - deficit_pct
    
    return percentile_rank, current_close, window_size


def get_daily_signal(
    df: pd.DataFrame,
    date_str: str,
    years: int = 10,
    low_percent: float = 40.0,
    high_top_percent: float = 3.0,
) -> DailySignal:
    """
    根据给定日期，计算买入/卖出信号
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d")

    # 将输入日期对齐到最近的向前交易日
    trading_date = get_nearest_trading_date(df, target_date, direction="backward")
    if trading_date is None:
        raise ValueError("数据中不存在早于该日期的交易日。")

    current_close, low_th, high_th, low_ref_date, high_ref_date = compute_thresholds(
        df, trading_date, years=years, low_percent=low_percent, high_top_percent=high_top_percent
    )

    if current_close < low_th:
        action = "BUY"
        reason = "收盘价低于近{:.0f}年最低的{:.0f}%阈值，可买入".format(years, low_percent)
    elif current_close > high_th:
        action = "SELL"
        reason = "收盘价高于近{:.0f}年最高的{:.0f}%阈值，可卖出（清仓）".format(years, high_top_percent)
    else:
        action = "HOLD"
        reason = "收盘价处于区间内，观望/持有"

    return DailySignal(
        trade_date=trading_date.to_pydatetime(),
        close=current_close,
        low_threshold=low_th,
        high_threshold=high_th,
        action=action,
        reason=reason,
        low_threshold_date=low_ref_date.to_pydatetime(),
        high_threshold_date=high_ref_date.to_pydatetime(),
    )


def backtest_strategy(
    df: pd.DataFrame,
    start_date_str: str,
    years: int = 10,
    low_percent: float = 40.0,
    high_top_percent: float = 3.0,
    step_drawdown: float = 0.05,
    max_additional_buys: int = 5,
    m_months: int = 3,
    base_invest: float = 10000.0,
) -> Tuple[float, List[TradeRecord]]:
    """
    按规则从指定日期回测到数据最后日期，返回总收益率和交易记录。

    规则：
    - 价格 < 低位阈值 → 开仓买入 base_invest
    - 持仓后，如价格相对上次买入价每再跌 step_drawdown（默认5%），
      且加仓次数未超过 max_additional_buys，则再买入 base_invest
    - 持仓后，距离上次买入已满 m_months 个月，且当前价格仍低于近N年的低位x%阈值，
      也可以加仓一次（与上述跌幅加仓共用同一加仓计数，总加仓次数不超过 max_additional_buys）
    - 价格 > 高位阈值 → 清仓卖出
    - 每次清仓后才允许下一次重新按规则买入
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

    # 起始交易日：优先向后找最近一个交易日，若没有则向前找最近一个交易日
    first_trade_date = get_nearest_trading_date(df, start_date, direction="forward")
    if first_trade_date is None:
        first_trade_date = get_nearest_trading_date(df, start_date, direction="backward")
    if first_trade_date is None:
        raise ValueError("数据中不存在可用于回测的交易日。")

    end_date = df[DATE_COL].max()

    # 账户初始资金：最多会出现 1 + max_additional_buys 次买入
    initial_capital = base_invest * (1 + max_additional_buys)
    cash = initial_capital
    position_shares = 0.0
    in_position = False
    last_buy_price: Optional[float] = None
    last_buy_date: Optional[pd.Timestamp] = None
    cycle_id = 0
    add_count = 0
    cycle_total_cost: float = 0.0  # 当前周期的总买入成本
    cycle_start_date: Optional[datetime] = None  # 当前周期第一次买入日期

    trades: List[TradeRecord] = []

    # 仅遍历回测区间内的交易日
    backtest_df = df[(df[DATE_COL] >= first_trade_date) & (df[DATE_COL] <= end_date)].copy()

    for _, row in backtest_df.iterrows():
        trade_date = row[DATE_COL]
        price = float(row[CLOSE_COL])

        # 每天都根据过去N年的数据计算阈值（不使用未来信息）
        try:
            current_close, low_th, high_th, low_ref_date, high_ref_date = compute_thresholds(
                df,
                trade_date,
                years=years,
                low_percent=low_percent,
                high_top_percent=high_top_percent,
            )
        except ValueError:
            # 如果窗口内没有足够的数据，跳过该日
            continue

        # 若当前无持仓，先看是否需要开仓
        if not in_position:
            if current_close < low_th:
                # 开仓
                shares = base_invest / price
                if cash < base_invest:
                    # 资金不足则跳过
                    continue

                cash -= base_invest
                position_shares += shares
                in_position = True
                cycle_id += 1
                last_buy_price = price
                last_buy_date = trade_date
                add_count = 0
                cycle_total_cost = base_invest  # 初始化周期总成本
                cycle_start_date = trade_date  # 记录本周期开始日期

                trades.append(
                    TradeRecord(
                        cycle_id=cycle_id,
                        date=trade_date.to_pydatetime(),
                        action="BUY",
                        price=price,
                        amount=base_invest,
                        shares=shares,
                        reason=(
                            "收盘价低于低位阈值"
                            f"（阈值参考：{low_ref_date.date()}，收盘价{low_th:.2f}），开仓买入"
                        ),
                        low_threshold=low_th,
                    )
                )
            # 无持仓时不再进行其它操作
            continue

        # 有持仓时，首先检查是否达到高位阈值 → 清仓
        if current_close > high_th:
            sell_amount = position_shares * price
            cash += sell_amount
            
            # 计算周期收益率
            cycle_return_pct = (sell_amount / cycle_total_cost - 1.0) * 100.0 if cycle_total_cost > 0 else 0.0

            # 计算本买卖周期经历的天数
            cycle_days: Optional[int] = None
            if cycle_start_date is not None:
                cycle_days = (trade_date - cycle_start_date).days + 1

            trades.append(
                TradeRecord(
                    cycle_id=cycle_id,
                    date=trade_date.to_pydatetime(),
                    action="SELL",
                    price=price,
                    amount=sell_amount,
                    shares=-position_shares,
                    reason=(
                        "收盘价高于高位阈值"
                        f"（阈值参考：{high_ref_date.date()}，收盘价{high_th:.2f}），清仓卖出"
                    ),
                    high_threshold=high_th,
                    cycle_return=cycle_return_pct,
                    cycle_days=cycle_days,
                )
            )

            # 清空持仓，等待下一次信号
            position_shares = 0.0
            in_position = False
            last_buy_price = None
            last_buy_date = None
            add_count = 0
            cycle_total_cost = 0.0
            cycle_start_date = None
            continue

        # 未触及卖出条件 → 考虑是否加仓
        can_add_more = (
            add_count < max_additional_buys
            and cash >= base_invest
            and last_buy_price is not None
            and last_buy_date is not None
        )

        if can_add_more:
            did_add = False

            # 规则1：相对上次买入价每再跌 step_drawdown 即加仓
            if price <= last_buy_price * (1.0 - step_drawdown):
                shares = base_invest / price
                cash -= base_invest
                position_shares += shares
                last_buy_price = price
                last_buy_date = trade_date
                add_count += 1
                cycle_total_cost += base_invest  # 累加周期总成本

                trades.append(
                    TradeRecord(
                        cycle_id=cycle_id,
                        date=trade_date.to_pydatetime(),
                        action="BUY_ADD",
                        price=price,
                        amount=base_invest,
                        shares=shares,
                        reason=f"相对上次买入价下跌{step_drawdown*100:.1f}%，第{add_count}次加仓",
                    )
                )
                did_add = True

            # 规则2：距离上次买入已满 m_months 个月，且价格仍低于低位x%阈值 → 也可加仓
            # 若当天已因规则1加仓，则不再重复加仓
            if (not did_add) and (m_months > 0):
                next_add_date = last_buy_date + pd.DateOffset(months=m_months)
                if trade_date >= next_add_date and price < low_th:
                    shares = base_invest / price
                    cash -= base_invest
                    position_shares += shares
                    last_buy_price = price
                    last_buy_date = trade_date
                    add_count += 1
                    cycle_total_cost += base_invest

                    trades.append(
                        TradeRecord(
                            cycle_id=cycle_id,
                            date=trade_date.to_pydatetime(),
                            action="BUY_ADD",
                            price=price,
                            amount=base_invest,
                            shares=shares,
                            reason=(
                                f"距离上次买入已满{m_months}个月，且价格低于低位阈值，"
                                f"第{add_count}次加仓"
                            ),
                        )
                    )

    # 回测结束时的总资产（若仍有持仓，按最后收盘价市值计算）
    final_price = float(df[df[DATE_COL] == end_date].iloc[0][CLOSE_COL])
    final_value = cash + position_shares * final_price
    total_return = (final_value / initial_capital - 1.0) * 100.0

    return total_return, trades


def get_percentile_position(
    df: pd.DataFrame,
    date_str: str,
    years: int = 5,
) -> dict:
    """
    获取指定日期的收盘价百分位位置信息
    
    返回字典包含:
        - date: 交易日期
        - close: 收盘价
        - percentile_rank: 百分位排名
        - years: 回溯年数
        - description: 描述性文字
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # 将输入日期对齐到最近的向前交易日
    trading_date = get_nearest_trading_date(df, target_date, direction="backward")
    if trading_date is None:
        raise ValueError("数据中不存在早于该日期的交易日。")
    
    percentile_rank, current_close, window_size = compute_percentile_rank(
        df, trading_date, years=years
    )
    
    # 生成描述性文字
    if percentile_rank > 100:
        description = f"收盘价高于近{years}年所有价格，超出{(percentile_rank-100):.1f}%"
    elif percentile_rank < 0:
        description = f"收盘价低于近{years}年所有价格，低于{abs(percentile_rank):.1f}%"
    else:
        description = f"收盘价高于近{years}年{percentile_rank:.1f}%的价格水平"
    
    return {
        "date": trading_date.to_pydatetime(),
        "close": current_close,
        "percentile_rank": percentile_rank,
        "years": years,
        "window_size": window_size,
        "description": description,
    }


def main():
    # 读取数据
    df = load_index_data()

    # print(f"Sheet名称: {SHEET_NAME}")
    # 交互输入
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_str = input(f"请输入日期 (YYYY-MM-DD)，默认 {today_str}: ").strip() or today_str

    years_str = input("请输入向前回溯的年数（默认10）: ").strip() or "10"
    low_pct_str = input("请输入低位区间百分比x（默认40，表示最低的40%）: ").strip() or "40"
    high_top_pct_str = input("请输入高位区间百分比y（默认3，表示最高的3%）: ").strip() or "3"
    m_months_str = input("请输入满月加仓间隔m（单位：月，默认3）: ").strip() or "3"

    years = int(years_str)
    low_pct = float(low_pct_str)
    high_top_pct = float(high_top_pct_str)
    m_months = int(m_months_str)

    # 单日信号
    daily_signal = get_daily_signal(
        df,
        date_str=date_str,
        years=years,
        low_percent=low_pct,
        high_top_percent=high_top_pct,
    )

    # 计算百分位位置
    percentile_info = get_percentile_position(
        df,
        date_str=date_str,
        years=years,
    )

    print("\n=== 单日买卖信号 ===")
    print(f"交易日：{daily_signal.trade_date.date()}")
    print(f"收盘价：{daily_signal.close:.2f}")
    if daily_signal.low_threshold_date is not None:
        print(
            f"近{years}年最低的{low_pct:.0f}%阈值价格：{daily_signal.low_threshold:.2f}"
            f"（阈值参考日期：{daily_signal.low_threshold_date.date()}）"
        )
    else:
        print(f"近{years}年最低的{low_pct:.0f}%阈值价格：{daily_signal.low_threshold:.2f}")

    if daily_signal.high_threshold_date is not None:
        print(
            f"近{years}年最高的{high_top_pct:.0f}%阈值价格：{daily_signal.high_threshold:.2f}"
            f"（阈值参考日期：{daily_signal.high_threshold_date.date()}）"
        )
    else:
        print(f"近{years}年最高的{high_top_pct:.0f}%阈值价格：{daily_signal.high_threshold:.2f}")
    print(f"信号：{daily_signal.action}（{daily_signal.reason}）")

    print("\n=== 百分位排名 ===")
    print(f"交易日：{percentile_info['date'].date()}")
    print(f"收盘价：{percentile_info['close']:.2f}")
    print(f"样本数量：{percentile_info['window_size']}个交易日")
    print(f"百分位排名：{percentile_info['percentile_rank']:.1f}%")
    print(f"说明：{percentile_info['description']}")

    # 回测收益
    print("\n=== 回测结果（从该日期至最近数据日期） ===")
    max_additional_buys = 5  # 总加仓次数上限（不含首笔建仓），与 backtest_strategy 默认值保持一致

    total_return, trades = backtest_strategy(
        df,
        start_date_str=date_str,
        years=years,
        low_percent=low_pct,
        high_top_percent=high_top_pct,
        max_additional_buys=max_additional_buys,
        m_months=m_months,
    )

    # 总周期天数：
    # - 若最后一个周期已经卖出：使用“最后一次卖出日期 - 第一次买入日期 + 1天”
    # - 若最后一个周期尚未卖出：使用“数据最后交易日 - 第一次买入日期 + 1天”
    first_buy_date: Optional[datetime] = None
    last_sell_date: Optional[datetime] = None
    max_cycle_id: Optional[int] = None
    for t in trades:
        # 记录第一笔买入（或加仓）日期
        if t.action in ("BUY", "BUY_ADD"):
            if first_buy_date is None or t.date < first_buy_date:
                first_buy_date = t.date
        # 记录最后一次卖出日期
        if t.action == "SELL":
            if last_sell_date is None or t.date > last_sell_date:
                last_sell_date = t.date
        # 记录最大的周期编号（用于判断最后一个周期是否已平仓）
        if max_cycle_id is None or t.cycle_id > max_cycle_id:
            max_cycle_id = t.cycle_id

    # 判断最后一个周期是否已经有卖出记录
    last_cycle_has_sell = False
    if max_cycle_id is not None:
        for t in trades:
            if t.cycle_id == max_cycle_id and t.action == "SELL":
                last_cycle_has_sell = True
                break

    if first_buy_date is not None:
        if last_cycle_has_sell and last_sell_date is not None:
            # 所有周期都已平仓：以最后一次卖出日期为结束
            end_date_for_total = last_sell_date
        else:
            # 存在未平仓的最后一个周期：以数据的最后一个交易日为结束
            end_date_for_total = df[DATE_COL].max().to_pydatetime()
        total_cycle_days = (end_date_for_total - first_buy_date).days + 1
    else:
        total_cycle_days = 0
    total_cycle_years = total_cycle_days / 365.0 if total_cycle_days > 0 else 0.0

    for t in trades:
        output_line = (
            f"[周期{t.cycle_id}] {t.date.date()} {t.action:7s} "
            f"价：{t.price:8.2f} 金额：{t.amount:10.2f} 股数：{t.shares:10.4f} 原因：{t.reason}"
        )
        # 如果是卖出操作，显示周期收益率和周期天数（兼容换算为多少年）
        if t.action == "SELL":
            if t.cycle_return is not None:
                output_line += f" | 周期收益率：{t.cycle_return:.2f}%"
            if t.cycle_days is not None:
                years_span = t.cycle_days / 365.0
                output_line += f" | 周期天数：{t.cycle_days}天（约{years_span:.2f}年）"
        print(output_line)

    initial_capital_print = 10000.0 * (1 + max_additional_buys)
    print(
        f"\n策略总收益率：{total_return:.2f}%"
        f"（初始资金按 {initial_capital_print:.0f} 元计算，总周期天数：{total_cycle_days}天（约{total_cycle_years:.2f}年））"
    )


if __name__ == "__main__":
    main()

