import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd

EXCEL_PATH = "output/彩票数据（双色球、大乐透）.xlsx"


@dataclass
class SsqRecord:
    date: datetime
    reds: List[int]
    blues: List[int]


@dataclass
class DltRecord:
    date: datetime
    fronts: List[int]
    backs: List[int]


def _normalize_draw_date(series: pd.Series) -> pd.Series:
    """
    清洗诸如 “2026-01-20(二)” 的括号信息，仅保留日期，并转为 datetime
    """
    cleaned = (
        series.astype(str)
        .str.replace(r"[\\(（].*?[\\)）]", "", regex=True)
        .str.strip()
    )
    parsed = pd.to_datetime(cleaned, format="%Y-%m-%d", errors="coerce")
    return parsed


def load_lottery_data(excel_path: str = EXCEL_PATH) -> Tuple[List[SsqRecord], List[DltRecord]]:
    """读取双色球与大乐透数据，并转为结构化记录列表"""
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"未找到彩票数据文件：{excel_path}")

    ssq_df = pd.read_excel(excel_path, sheet_name="双色球", engine="openpyxl")
    dlt_df = pd.read_excel(excel_path, sheet_name="大乐透", engine="openpyxl")

    ssq_df["开奖日期_dt"] = _normalize_draw_date(ssq_df.get("开奖日期"))
    dlt_df["开奖日期_dt"] = _normalize_draw_date(dlt_df.get("开奖日期"))

    ssq_records: List[SsqRecord] = []
    for _, row in ssq_df.iterrows():
        if pd.isna(row.get("开奖日期_dt")):
            continue
        reds_raw = [
            row.get("红球1"),
            row.get("红球2"),
            row.get("红球3"),
            row.get("红球4"),
            row.get("红球5"),
            row.get("红球6"),
        ]
        blues_raw = [row.get("蓝球")]
        try:
            reds = [int(x) for x in reds_raw if pd.notna(x)]
            blues = [int(x) for x in blues_raw if pd.notna(x)]
        except ValueError:
            continue
        if len(reds) != 6 or len(blues) != 1:
            # 跳过数据不完整的行
            continue
        ssq_records.append(
            SsqRecord(
                date=row["开奖日期_dt"].to_pydatetime(),
                reds=sorted(reds),
                blues=blues,
            )
        )

    dlt_records: List[DltRecord] = []
    for _, row in dlt_df.iterrows():
        if pd.isna(row.get("开奖日期_dt")):
            continue
        fronts_raw = [
            row.get("前区1"),
            row.get("前区2"),
            row.get("前区3"),
            row.get("前区4"),
            row.get("前区5"),
        ]
        backs_raw = [row.get("后区1"), row.get("后区2")]
        try:
            fronts = [int(x) for x in fronts_raw if pd.notna(x)]
            backs = [int(x) for x in backs_raw if pd.notna(x)]
        except ValueError:
            continue
        if len(fronts) != 5 or len(backs) != 2:
            continue
        dlt_records.append(
            DltRecord(
                date=row["开奖日期_dt"].to_pydatetime(),
                fronts=sorted(fronts),
                backs=sorted(backs),
            )
        )

    if not ssq_records:
        raise ValueError("未成功解析任何双色球记录，请检查源数据格式。")
    if not dlt_records:
        raise ValueError("未成功解析任何大乐透记录，请检查源数据格式。")

    return ssq_records, dlt_records


def _score_numbers_by_freq_and_mean(
    numbers: List[int],
    possible_range: range,
    mean_weight: float = 0.1,
) -> List[int]:
    """
    根据数字出现频次与整体平均值的偏离程度为每个数字打分：
    score(num) = 频次 - mean_weight * |num - 全局平均值|
    分数越高越“优先”
    """
    counter = Counter(numbers)
    if not numbers:
        # 回退：按号码自然顺序
        return list(possible_range)

    global_mean = float(np.mean(numbers))
    scored: List[Tuple[int, float]] = []
    for n in possible_range:
        freq = counter.get(n, 0)
        penalty = abs(n - global_mean)
        score = freq - mean_weight * penalty
        scored.append((n, score))

    # 按分数从高到低排序，分数相同则号码小的在前
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [n for n, _ in scored]


def _make_groups_from_pool(
    sorted_pool: List[int],
    group_size: int,
    max_groups: int,
) -> List[List[int]]:
    """从排好序的号码池中用滑动窗口构造若干组号码"""
    groups: List[List[int]] = []
    if len(sorted_pool) < group_size:
        return groups
    max_start = len(sorted_pool) - group_size + 1
    for start in range(max_start):
        group = sorted(sorted_pool[start : start + group_size])
        groups.append(group)
        if len(groups) >= max_groups:
            break
    return groups


def select_best_ssq_combinations(
    records: List[SsqRecord],
    max_combinations: int = 6,
) -> List[Dict[str, Any]]:
    """
    根据历史数据中号码出现频次与整体平均值，挑选若干组“最佳”双色球号码。
    返回的每项包含：{'reds': [6个红球], 'blue': 蓝球}
    """
    all_reds: List[int] = []
    all_blues: List[int] = []
    for r in records:
        all_reds.extend(r.reds)
        all_blues.extend(r.blues)

    # 按“频次 + 接近平均值”打分
    sorted_red_nums = _score_numbers_by_freq_and_mean(
        all_reds, possible_range=range(1, 33 + 1), mean_weight=0.1
    )
    sorted_blue_nums = _score_numbers_by_freq_and_mean(
        all_blues, possible_range=range(1, 16 + 1), mean_weight=0.1
    )

    # 取前若干个号码作为候选池，再用滑动窗口拼成不同组合
    red_pool = sorted_red_nums[:12]  # 历史上更“活跃”的红球
    blue_pool = sorted_blue_nums[:4]  # 更“活跃”的蓝球

    red_groups = _make_groups_from_pool(red_pool, group_size=6, max_groups=3)
    # 蓝球只需要单个数字，不需要成组
    blue_candidates = blue_pool[:2] if blue_pool else sorted_blue_nums[:2]

    combinations: List[Dict[str, Any]] = []
    for rg in red_groups:
        for b in blue_candidates:
            combinations.append({"reds": rg, "blue": b})
            if len(combinations) >= max_combinations:
                return combinations

    return combinations


def select_best_ssq_single(records: List[SsqRecord]) -> Dict[str, Any]:
    """
    在给定历史记录上生成“单个”最佳双色球号码组合。
    """
    combos = select_best_ssq_combinations(records, max_combinations=1)
    return combos[0] if combos else {}


def select_best_dlt_combinations(
    records: List[DltRecord],
    max_combinations: int = 6,
) -> List[Dict[str, Any]]:
    """
    根据历史数据中号码出现频次与整体平均值，挑选若干组“最佳”大乐透号码。
    返回的每项包含：{'fronts': [5个前区], 'backs': [2个后区]}
    """
    all_fronts: List[int] = []
    all_backs: List[int] = []
    for r in records:
        all_fronts.extend(r.fronts)
        all_backs.extend(r.backs)

    sorted_front_nums = _score_numbers_by_freq_and_mean(
        all_fronts, possible_range=range(1, 35 + 1), mean_weight=0.1
    )
    sorted_back_nums = _score_numbers_by_freq_and_mean(
        all_backs, possible_range=range(1, 12 + 1), mean_weight=0.1
    )

    front_pool = sorted_front_nums[:12]
    back_pool = sorted_back_nums[:6]

    front_groups = _make_groups_from_pool(front_pool, group_size=5, max_groups=3)
    back_groups = _make_groups_from_pool(back_pool, group_size=2, max_groups=3)

    combinations: List[Dict[str, Any]] = []
    for fg in front_groups:
        for bg in back_groups:
            combinations.append({"fronts": fg, "backs": bg})
            if len(combinations) >= max_combinations:
                return combinations

    return combinations


def select_best_dlt_single(records: List[DltRecord]) -> Dict[str, Any]:
    """
    在给定历史记录上生成“单个”最佳大乐透号码组合。
    """
    combos = select_best_dlt_combinations(records, max_combinations=1)
    return combos[0] if combos else {}


def _filter_recent_records(
    records: List[Any],
    years: int,
) -> List[Any]:
    """根据开奖日期过滤出近 N 年记录"""
    if not records:
        return []
    latest_date = max(r.date for r in records)
    # 使用年份差阈值，大致近 N 年
    cutoff = latest_date.replace(year=latest_date.year - years)
    return [r for r in records if r.date >= cutoff]


def _get_past_window(
    records: List[Any],
    as_of_date: datetime,
    years: int,
) -> List[Any]:
    """
    只取某期开奖日期 as_of_date 之前、且在向前 N 年窗口内的历史记录，
    用于“走进式回测”：每一期仅用当期之前的数据来训练。
    """
    if not records:
        return []
    window_start = as_of_date - timedelta(days=years * 365)
    return [r for r in records if window_start <= r.date < as_of_date]


def evaluate_ssq_combinations(
    combinations: List[Dict[str, Any]],
    records: List[SsqRecord],
) -> List[Dict[str, Any]]:
    """
    对给定双色球组合在指定样本（一般是近N年记录）上进行回测，
    计算平均匹配度等指标。
    """
    results: List[Dict[str, Any]] = []
    total_draws = len(records)
    if total_draws == 0:
        return results

    for combo in combinations:
        reds_c = set(combo["reds"])
        blue_c = combo["blue"]

        total_red_matches = 0
        total_blue_matches = 0
        hit_ge3_red = 0  # 至少3个红球命中期数
        hit_ge4_red = 0  # 至少4个红球命中期数
        hit_any_blue = 0
        full_match = 0   # 6+1 全中

        for r in records:
            red_m = len(reds_c.intersection(r.reds))
            blue_m = 1 if blue_c in r.blues else 0

            total_red_matches += red_m
            total_blue_matches += blue_m

            if red_m >= 3:
                hit_ge3_red += 1
            if red_m >= 4:
                hit_ge4_red += 1
            if blue_m >= 1:
                hit_any_blue += 1
            if red_m == 6 and blue_m == 1:
                full_match += 1

        avg_red = total_red_matches / total_draws
        avg_blue = total_blue_matches / total_draws
        # 将红球与蓝球命中比例简单平均，作为“匹配度”指标
        accuracy = (
            (total_red_matches / (total_draws * 6))
            + (total_blue_matches / (total_draws * 1))
        ) / 2.0 * 100.0

        results.append(
            {
                "reds": combo["reds"],
                "blue": combo["blue"],
                "total_draws": total_draws,
                "avg_red_matches": avg_red,
                "avg_blue_matches": avg_blue,
                "hit_ge3_red": hit_ge3_red,
                "hit_ge4_red": hit_ge4_red,
                "hit_any_blue": hit_any_blue,
                "full_match": full_match,
                "accuracy_percent": accuracy,
            }
        )

    # 按匹配度从高到低排序
    results.sort(key=lambda x: -x["accuracy_percent"])
    return results


def backtest_ssq_walk_forward(
    records: List[SsqRecord],
    years: int = 5,
) -> Dict[str, Any]:
    """
    走进式回测（更贴近你说的“只用当天以前的数据生成号码再对比当天结果”）：
    - 选取近 years 年内的每一期开奖作为测试点；
    - 对于每一期，使用“该期之前 years 年内”的历史记录生成最多 max_combinations 组号码；
    - 计算在这些号码中，“最好的一组”对该期实际结果的命中情况；
    - 汇总所有测试期的平均命中数和整体匹配度。
    """
    if not records:
        return {}

    # 确保按日期排序
    records_sorted = sorted(records, key=lambda r: r.date)
    latest_date = records_sorted[-1].date
    eval_start = latest_date - timedelta(days=years * 365)

    total_draws = 0
    skipped_draws = 0

    sum_best_red = 0.0
    sum_best_blue = 0.0
    ge3_red = 0
    ge4_red = 0
    any_blue = 0
    full_hit = 0

    for rec in records_sorted:
        if rec.date < eval_start:
            continue

        # 训练集：只用当天以前 N 年的数据
        train_window = _get_past_window(records_sorted, rec.date, years)
        if not train_window:
            skipped_draws += 1
            continue

        combo = select_best_ssq_single(train_window)
        if not combo:
            skipped_draws += 1
            continue

        reds_c = set(combo["reds"])
        blue_c = combo["blue"]
        best_red = len(reds_c.intersection(rec.reds))
        best_blue = 1 if blue_c in rec.blues else 0
        best_full = best_red == 6 and best_blue == 1

        total_draws += 1
        sum_best_red += best_red
        sum_best_blue += best_blue

        if best_red >= 3:
            ge3_red += 1
        if best_red >= 4:
            ge4_red += 1
        if best_blue >= 1:
            any_blue += 1
        if best_full:
            full_hit += 1

    if total_draws == 0:
        return {
            "total_draws": 0,
            "skipped_draws": skipped_draws,
        }

    avg_red = sum_best_red / total_draws
    avg_blue = sum_best_blue / total_draws
    accuracy = (
        (sum_best_red / (total_draws * 6))
        + (sum_best_blue / (total_draws * 1))
    ) / 2.0 * 100.0

    return {
        "years": years,
        "total_draws": total_draws,
        "skipped_draws": skipped_draws,
        "avg_best_red_matches": avg_red,
        "avg_best_blue_matches": avg_blue,
        "ge3_red_draws": ge3_red,
        "ge4_red_draws": ge4_red,
        "any_blue_draws": any_blue,
        "full_match_draws": full_hit,
        "accuracy_percent": accuracy,
    }


def evaluate_dlt_combinations(
    combinations: List[Dict[str, Any]],
    records: List[DltRecord],
) -> List[Dict[str, Any]]:
    """
    对给定大乐透组合在指定样本（一般是近N年记录）上进行回测，
    计算平均匹配度等指标。
    """
    results: List[Dict[str, Any]] = []
    total_draws = len(records)
    if total_draws == 0:
        return results

    for combo in combinations:
        fronts_c = set(combo["fronts"])
        backs_c = set(combo["backs"])

        total_front_matches = 0
        total_back_matches = 0
        hit_ge3_front = 0
        hit_ge4_front = 0
        hit_any_back = 0
        full_match = 0  # 5+2 全中

        for r in records:
            front_m = len(fronts_c.intersection(r.fronts))
            back_m = len(backs_c.intersection(r.backs))

            total_front_matches += front_m
            total_back_matches += back_m

            if front_m >= 3:
                hit_ge3_front += 1
            if front_m >= 4:
                hit_ge4_front += 1
            if back_m >= 1:
                hit_any_back += 1
            if front_m == 5 and back_m == 2:
                full_match += 1

        avg_front = total_front_matches / total_draws
        avg_back = total_back_matches / total_draws
        accuracy = (
            (total_front_matches / (total_draws * 5))
            + (total_back_matches / (total_draws * 2))
        ) / 2.0 * 100.0

        results.append(
            {
                "fronts": combo["fronts"],
                "backs": combo["backs"],
                "total_draws": total_draws,
                "avg_front_matches": avg_front,
                "avg_back_matches": avg_back,
                "hit_ge3_front": hit_ge3_front,
                "hit_ge4_front": hit_ge4_front,
                "hit_any_back": hit_any_back,
                "full_match": full_match,
                "accuracy_percent": accuracy,
            }
        )

    results.sort(key=lambda x: -x["accuracy_percent"])
    return results


def backtest_dlt_walk_forward(
    records: List[DltRecord],
    years: int = 5,
) -> Dict[str, Any]:
    """
    大乐透走进式回测，逻辑同 backtest_ssq_walk_forward。
    """
    if not records:
        return {}

    records_sorted = sorted(records, key=lambda r: r.date)
    latest_date = records_sorted[-1].date
    eval_start = latest_date - timedelta(days=years * 365)

    total_draws = 0
    skipped_draws = 0

    sum_best_front = 0.0
    sum_best_back = 0.0
    ge3_front = 0
    ge4_front = 0
    any_back = 0
    full_hit = 0

    for rec in records_sorted:
        if rec.date < eval_start:
            continue

        train_window = _get_past_window(records_sorted, rec.date, years)
        if not train_window:
            skipped_draws += 1
            continue

        combo = select_best_dlt_single(train_window)
        if not combo:
            skipped_draws += 1
            continue

        fronts_c = set(combo["fronts"])
        backs_c = set(combo["backs"])
        best_front = len(fronts_c.intersection(rec.fronts))
        best_back = len(backs_c.intersection(rec.backs))
        best_full = best_front == 5 and best_back == 2

        total_draws += 1
        sum_best_front += best_front
        sum_best_back += best_back

        if best_front >= 3:
            ge3_front += 1
        if best_front >= 4:
            ge4_front += 1
        if best_back >= 1:
            any_back += 1
        if best_full:
            full_hit += 1

    if total_draws == 0:
        return {
            "total_draws": 0,
            "skipped_draws": skipped_draws,
        }

    avg_front = sum_best_front / total_draws
    avg_back = sum_best_back / total_draws
    accuracy = (
        (sum_best_front / (total_draws * 5))
        + (sum_best_back / (total_draws * 2))
    ) / 2.0 * 100.0

    return {
        "years": years,
        "total_draws": total_draws,
        "skipped_draws": skipped_draws,
        "avg_best_front_matches": avg_front,
        "avg_best_back_matches": avg_back,
        "ge3_front_draws": ge3_front,
        "ge4_front_draws": ge4_front,
        "any_back_draws": any_back,
        "full_match_draws": full_hit,
        "accuracy_percent": accuracy,
    }


def main(n_years: int = 5) -> None:
    """
    根据历史数据，挑选推荐的双色球与大乐透号码，并回测近 N 年的匹配度。
    """
    print("=" * 60)
    print(f"从 {EXCEL_PATH} 加载历史彩票数据...")
    ssq_records, dlt_records = load_lottery_data(EXCEL_PATH)
    print(f"  双色球记录数：{len(ssq_records)}")
    print(f"  大乐透记录数：{len(dlt_records)}")

    # 1. 用全部历史数据各选出“单个最佳号码组合”
    ssq_best = select_best_ssq_single(ssq_records)
    dlt_best = select_best_dlt_single(dlt_records)

    print("\n=== 当前推荐的双色球最佳号码（单注） ===")
    if ssq_best:
        reds_str = " ".join(f"{n:02d}" for n in ssq_best["reds"])
        print(f"红球 [{reds_str}]  蓝球 [{ssq_best['blue']:02d}]")
    else:
        print("无法生成双色球推荐号码，请检查数据。")

    print("\n=== 当前推荐的大乐透最佳号码（单注） ===")
    if dlt_best:
        fronts_str = " ".join(f"{n:02d}" for n in dlt_best["fronts"])
        backs_str = " ".join(f"{n:02d}" for n in dlt_best["backs"])
        print(f"前区 [{fronts_str}]  后区 [{backs_str}]")
    else:
        print("无法生成大乐透推荐号码，请检查数据。")

    # 2. 使用“走进式回测”逻辑：每一期只用该期以前 N 年的数据来选号码
    print(f"\n=== 走进式回测：近 {n_years} 年，每期开奖仅用当期以前数据训练 ===")
    ssq_walk = backtest_ssq_walk_forward(ssq_records, years=n_years)
    dlt_walk = backtest_dlt_walk_forward(dlt_records, years=n_years)

    print("\n--- 双色球策略走进式回测汇总 ---")
    if ssq_walk.get("total_draws", 0) == 0:
        print("可用于回测的期数为 0，请检查数据是否足够。")
    else:
        print(
            f"参与回测期数：{ssq_walk['total_draws']} 期，"
            f"因缺少历史窗口而跳过：{ssq_walk['skipped_draws']} 期"
        )
        print(
            f"平均每期最佳红球命中：{ssq_walk['avg_best_red_matches']:.2f} 个，"
            f"平均每期最佳蓝球命中：{ssq_walk['avg_best_blue_matches']:.2f} 个"
        )
        print(
            f"至少 3 红的期数：{ssq_walk['ge3_red_draws']}，"
            f"至少 4 红的期数：{ssq_walk['ge4_red_draws']}，"
            f"至少中 1 蓝的期数：{ssq_walk['any_blue_draws']}"
        )
        print(
            f"6+1 全中的期数：{ssq_walk['full_match_draws']}，"
            f"综合匹配度约：{ssq_walk['accuracy_percent']:.2f}%"
        )

    print("\n--- 大乐透策略走进式回测汇总 ---")
    if dlt_walk.get("total_draws", 0) == 0:
        print("可用于回测的期数为 0，请检查数据是否足够。")
    else:
        print(
            f"参与回测期数：{dlt_walk['total_draws']} 期，"
            f"因缺少历史窗口而跳过：{dlt_walk['skipped_draws']} 期"
        )
        print(
            f"平均每期最佳前区命中：{dlt_walk['avg_best_front_matches']:.2f} 个，"
            f"平均每期最佳后区命中：{dlt_walk['avg_best_back_matches']:.2f} 个"
        )
        print(
            f"至少 3 前区的期数：{dlt_walk['ge3_front_draws']}，"
            f"至少 4 前区的期数：{dlt_walk['ge4_front_draws']}，"
            f"至少中 1 个后区的期数：{dlt_walk['any_back_draws']}"
        )
        print(
            f"5+2 全中的期数：{dlt_walk['full_match_draws']}，"
            f"综合匹配度约：{dlt_walk['accuracy_percent']:.2f}%"
        )


if __name__ == "__main__":
    # 默认回测近5年的匹配度，如需调整可在此修改参数
    main(n_years=5)

