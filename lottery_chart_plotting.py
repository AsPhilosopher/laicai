import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

import pandas as pd


def _read_ssq_dlt(excel_file: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """读取双色球与大乐透数据并转换为易序列化的结构"""
    ssq_df = pd.read_excel(excel_file, sheet_name="双色球", engine="openpyxl")
    dlt_df = pd.read_excel(excel_file, sheet_name="大乐透", engine="openpyxl")

    def _normalize_date(series: pd.Series) -> pd.Series:
        # 清洗诸如 “2026-01-20(二)” 的括号信息，仅保留日期
        cleaned = (
            series.astype(str)
            .str.replace(r"[\\(（].*?[\\)）]", "", regex=True)
            .str.strip()
        )
        parsed = pd.to_datetime(cleaned, format="%Y-%m-%d", errors="coerce")
        return parsed

    ssq_df["开奖日期_dt"] = _normalize_date(ssq_df.get("开奖日期"))
    dlt_df["开奖日期_dt"] = _normalize_date(dlt_df.get("开奖日期"))

    def _rows_from_ssq(df: pd.DataFrame) -> List[Dict[str, Any]]:
        rows = []
        for _, row in df.iterrows():
            if pd.isna(row.get("开奖日期_dt")):
                continue
            reds = [
                row.get("红球1"),
                row.get("红球2"),
                row.get("红球3"),
                row.get("红球4"),
                row.get("红球5"),
                row.get("红球6"),
            ]
            blues = [row.get("蓝球")]
            try:
                reds = [int(x) for x in reds if pd.notna(x)]
                blues = [int(x) for x in blues if pd.notna(x)]
            except ValueError:
                continue
            rows.append(
                {
                    "date": row["开奖日期_dt"].strftime("%Y-%m-%d"),
                    "reds": reds,
                    "blues": blues,
                }
            )
        return rows

    def _rows_from_dlt(df: pd.DataFrame) -> List[Dict[str, Any]]:
        rows = []
        for _, row in df.iterrows():
            if pd.isna(row.get("开奖日期_dt")):
                continue
            fronts = [
                row.get("前区1"),
                row.get("前区2"),
                row.get("前区3"),
                row.get("前区4"),
                row.get("前区5"),
            ]
            backs = [row.get("后区1"), row.get("后区2")]
            try:
                fronts = [int(x) for x in fronts if pd.notna(x)]
                backs = [int(x) for x in backs if pd.notna(x)]
            except ValueError:
                continue
            rows.append(
                {
                    "date": row["开奖日期_dt"].strftime("%Y-%m-%d"),
                    "fronts": fronts,
                    "backs": backs,
                }
            )
        return rows

    return _rows_from_ssq(ssq_df), _rows_from_dlt(dlt_df)


def _default_output_path(excel_file: str) -> str:
    base_dir = os.path.dirname(excel_file)
    if not base_dir:
        base_dir = os.getcwd()
    return os.path.join(base_dir, "彩票走势图.html")


def _build_html(ssq_rows: List[Dict[str, Any]], dlt_rows: List[Dict[str, Any]]) -> str:
    """生成内嵌 Plotly + JS 交互的 HTML 字符串"""
    ssq_json = json.dumps(ssq_rows, ensure_ascii=False)
    dlt_json = json.dumps(dlt_rows, ensure_ascii=False)

    # 默认初始范围：近1年
    init_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    init_end = datetime.now().strftime("%Y-%m-%d")

    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>彩票数字统计（双色球 & 大乐透）</title>
  <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 20px; }}
    .controls {{ margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .charts {{ display: grid; grid-template-columns: 1fr; gap: 28px; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.04); }}
    h2 {{ margin: 0 0 8px; font-size: 18px; }}
    button {{ padding: 6px 10px; border: 1px solid #d1d5db; background: #fff; border-radius: 6px; cursor: pointer; }}
    button:hover {{ background: #f3f4f6; }}
    input[type="date"] {{ padding: 6px 8px; border-radius: 6px; border: 1px solid #d1d5db; }}
    @media (min-width: 1200px) {{
        .charts {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>
  <h1>彩票数字统计（双色球 / 大乐透）</h1>
  <div class="controls">
    <label>开始日期 <input type="date" id="startDate" value="{init_start}"/></label>
    <label>结束日期 <input type="date" id="endDate" value="{init_end}"/></label>
    <button data-range="90">近3个月</button>
    <button data-range="180">近6个月</button>
    <button data-range="365">近1年</button>
    <button data-range="1095">近3年</button>
    <button data-range="0">全部</button>
    <button id="applyRange">应用</button>
    <span id="info" style="margin-left:8px;color:#6b7280;"></span>
  </div>

  <div class="charts">
    <div class="card">
      <h2>双色球各数字出现次数（升序）</h2>
      <div id="ssqFreqRed" style="height:360px;"></div>
      <div id="ssqFreqBlue" style="height:300px; margin-top:12px;"></div>
    </div>
    <div class="card">
      <h2>大乐透各数字出现次数（升序）</h2>
      <div id="dltFreqFront" style="height:360px;"></div>
      <div id="dltFreqBack" style="height:300px; margin-top:12px;"></div>
    </div>
    <div class="card">
      <h2>双色球奇偶分布</h2>
      <div id="ssqParity"></div>
    </div>
    <div class="card">
      <h2>大乐透奇偶分布</h2>
      <div id="dltParity"></div>
    </div>
  </div>

  <script>
    const ssqData = {ssq_json};
    const dltData = {dlt_json};

    function parseDate(str) {{
      const d = new Date(str);
      return isNaN(d) ? null : d;
    }}

    function filterByRange(data, start, end, dateKey = 'date') {{
      return data.filter(item => {{
        const d = parseDate(item[dateKey]);
        return d && d >= start && d <= end;
      }});
    }}

    function countNumbers(records, key) {{
      const counter = new Map();
      records.forEach(r => {{
        (r[key] || []).forEach(n => {{
          const num = Number(n);
          if (Number.isFinite(num)) {{
            counter.set(num, (counter.get(num) || 0) + 1);
          }}
        }});
      }});
      return Array.from(counter.entries()).sort((a,b)=>a[1]-b[1]); // 升序
    }}

    function countParity(records, key) {{
      let odd = 0, even = 0;
      records.forEach(r => {{
        (r[key] || []).forEach(n => {{
          const num = Number(n);
          if (!Number.isFinite(num)) return;
          if (num % 2 === 0) even += 1; else odd += 1;
        }});
      }});
      return [odd, even];
    }}

    function renderFreq(divId, sortedCounts, title, color) {{
      // 将号码作为“类别”而不是数值轴，保证按出现次数排序后的顺序来显示
      const x = sortedCounts.map(item => String(item[0]));
      const y = sortedCounts.map(item => item[1]);
      const text = y.map(v => `${{v}} 次`);
      const data = [{{
        type: 'bar',
        x,
        y,
        text,
        textposition: 'auto',
        marker: {{ color }},
      }}];
      const layout = {{
        margin: {{t: 30, l: 50, r: 10, b: 60}},
        xaxis: {{
          title: '号码',
          automargin: true,
          type: 'category',
          categoryorder: 'array',
          // 使用当前 x 顺序（即按出现次数升序后的顺序）
          categoryarray: x,
        }},
        yaxis: {{title: '出现次数'}},
        title: {{text: title, x: 0.02, font: {{size: 14}}}},
        hovermode: 'closest',
      }};
      Plotly.react(divId, data, layout, {{displaylogo: false}});
    }}

    function renderParity(divId, redOddEven, blueOddEven, labels) {{
      const categories = labels;
      const odd = [redOddEven[0], blueOddEven[0]];
      const even = [redOddEven[1], blueOddEven[1]];
      const data = [
        {{type:'bar', name:'奇数', x: categories, y: odd, marker:{{color:'#f97316'}}, text: odd, textposition:'auto'}},
        {{type:'bar', name:'偶数', x: categories, y: even, marker:{{color:'#60a5fa'}}, text: even, textposition:'auto'}},
      ];
      const layout = {{
        barmode: 'group',
        margin: {{t: 30, l: 50, r: 10, b: 60}},
        yaxis: {{title:'出现次数'}},
        title: {{text:'奇偶分布', x:0.02, font:{{size:16}}}}
      }};
      Plotly.react(divId, data, layout, {{displaylogo:false}});
    }}

    function updateCharts() {{
      const startInput = document.getElementById('startDate').value;
      const endInput = document.getElementById('endDate').value;
      const start = parseDate(startInput) || new Date('1900-01-01');
      const end = parseDate(endInput) || new Date();
      end.setHours(23,59,59,999);

      const ssq = filterByRange(ssqData, start, end);
      const dlt = filterByRange(dltData, start, end);

      // 频次
      renderFreq('ssqFreqRed', countNumbers(ssq, 'reds'), '双色球 红球', '#ef4444');
      renderFreq('ssqFreqBlue', countNumbers(ssq, 'blues'), '双色球 蓝球', '#3b82f6');

      // 大乐透频次
      renderFreq('dltFreqFront', countNumbers(dlt, 'fronts'), '大乐透 前区', '#22d3ee');
      renderFreq('dltFreqBack', countNumbers(dlt, 'backs'), '大乐透 后区', '#a855f7');

      // 奇偶
      const ssqRedParity = countParity(ssq, 'reds');
      const ssqBlueParity = countParity(ssq, 'blues');
      renderParity('ssqParity', ssqRedParity, ssqBlueParity, ['红球','蓝球']);

      const dltFrontParity = countParity(dlt, 'fronts');
      const dltBackParity = countParity(dlt, 'backs');
      renderParity('dltParity', dltFrontParity, dltBackParity, ['前区','后区']);

      document.getElementById('info').textContent = `筛选后：双色球 ${{ssq.length}} 期，大乐透 ${{dlt.length}} 期`;
    }}

    document.getElementById('applyRange').addEventListener('click', updateCharts);
    document.querySelectorAll('button[data-range]').forEach(btn => {{
      btn.addEventListener('click', () => {{
        const days = Number(btn.dataset.range);
        if (days === 0) {{
          document.getElementById('startDate').value = '';
          document.getElementById('endDate').value = '';
        }} else {{
          const end = new Date();
          const start = new Date();
          start.setDate(end.getDate() - days);
          document.getElementById('startDate').value = start.toISOString().slice(0,10);
          document.getElementById('endDate').value = end.toISOString().slice(0,10);
        }}
        updateCharts();
      }});
    }});

    // 初次渲染
    updateCharts();
  </script>
</body>
</html>
"""


def generate_lottery_charts(
    excel_file: str = "output/彩票数据（双色球、大乐透）.xlsx",
    output_html: str = None,
) -> str:
    """读取Excel并生成包含时间选择器的交互式统计HTML"""
    print(f"读取数据文件: {excel_file}")
    ssq_rows, dlt_rows = _read_ssq_dlt(excel_file)
    print(f"  双色球记录: {len(ssq_rows)} 条, 大乐透记录: {len(dlt_rows)} 条")

    if output_html is None:
        output_html = _default_output_path(excel_file)

    html = _build_html(ssq_rows, dlt_rows)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML 已生成: {output_html}")
    return output_html


def main():
    generate_lottery_charts()


if __name__ == "__main__":
    main()