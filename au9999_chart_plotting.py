import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional
import os


def plot_gold_close_price(excel_file: str,
                          sheet_name: str = 0,
                          years: int = 3,
                          output_html: Optional[str] = None):
    """
    绘制黄金(Au99.99)收盘价折线图（HTML交互版）

    Args:
        excel_file: Excel 文件路径
        sheet_name: Sheet 名称或索引（默认第 1 个）
        years: 显示最近 N 年的数据
        output_html: 输出 HTML 路径；若为 None，则与 Excel 同目录，命名为“黄金Au99.99_近N年收盘价走势图.html”
    """
    print(f"正在读取Excel文件: {excel_file}")
    print(f"Sheet: {sheet_name}")
    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")

    required_cols = ["Date(日期)", "Close(收盘价)"]
    if any(col not in df.columns for col in required_cols):
        raise ValueError(f"缺少必要列，需包含: {required_cols}，当前列: {df.columns.tolist()}")

    # 规范日期列
    df["Date(日期)"] = pd.to_datetime(df["Date(日期)"], errors="coerce")
    df = df.dropna(subset=["Date(日期)"])

    # 过滤最近 N 年
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    df_filtered = df[df["Date(日期)"] >= start_date].copy()
    if df_filtered.empty:
        raise ValueError("筛选后无数据，请检查 years 参数或原始数据。")

    available_years = (df_filtered["Date(日期)"].max() - df_filtered["Date(日期)"].min()).days / 365.25
    df_filtered = df_filtered.sort_values("Date(日期)")

    print(f"筛选后数据量: {len(df_filtered)} 条")
    print(f"日期范围: {df_filtered['Date(日期)'].min()} 至 {df_filtered['Date(日期)'].max()}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_filtered["Date(日期)"],
        y=df_filtered["Close(收盘价)"],
        mode="lines",
        name="收盘价(元)",
        line=dict(color="#d4af37", width=2),
        hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br>" +
                      "<b>收盘价</b>: %{y:.2f}<br>" +
                      "<extra></extra>",
    ))

    fig.update_layout(
        title={
            "text": f"黄金(Au99.99) - 近{years}年收盘价走势图",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"}
        },
        xaxis=dict(
            title=dict(text="日期", font=dict(size=14)),
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            tickformat="%Y-%m-%d",
            dtick="M1",
            rangeselector=dict(
                buttons=(lambda span_years: (
                    [dict(count=1, label="1个月", step="month", stepmode="backward"),
                     dict(count=3, label="3个月", step="month", stepmode="backward"),
                     dict(count=6, label="6个月", step="month", stepmode="backward"),
                     dict(count=1, label="1年", step="year", stepmode="backward")] +
                    ([dict(count=3, label="3年", step="year", stepmode="backward")] if span_years > 3 else []) +
                    ([dict(count=5, label="5年", step="year", stepmode="backward")] if span_years > 5 else []) +
                    [dict(step="all", label="全部")]
                ))(available_years)
            ),
            rangeslider=dict(visible=True, thickness=0.05),
            type="date",
        ),
        yaxis=dict(
            title=dict(text="收盘价(元)", font=dict(size=14)),
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)"
        ),
        hovermode="x unified",
        template="plotly_white",
        height=700,
        margin=dict(l=60, r=30, t=80, b=60),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="rgba(0, 0, 0, 0.2)",
            borderwidth=1
        ),
    )

    if output_html is None:
        excel_dir = os.path.dirname(excel_file)
        if not excel_dir:
            excel_dir = os.getcwd()
        output_html = os.path.join(excel_dir, f"黄金Au99.99_近{years}年收盘价走势图.html")

    config = {
        "locale": "zh-cn",
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToAdd": [],
        "modeBarButtonsToRemove": [],
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"黄金Au99.99_近{years}年收盘价走势图",
            "height": 700,
            "width": 1400,
            "scale": 1
        }
    }

    html_content = fig.to_html(include_plotlyjs="cdn", config=config, full_html=True)
    # 注入 Plotly 官方中文 locale，并强制全局使用中文，同时修正"下载图片"按钮的英文 tooltip
    zh_locale_inject = (
        "\n<!-- Plotly 中文语言包（用于工具栏提示/按钮文案等） -->\n"
        "<script src=\"https://cdn.plot.ly/plotly-locale-zh-cn-latest.js\"></script>\n"
        "<script>\n"
        "  (function(){\n"
        "    if (window.Plotly && Plotly.setPlotConfig) {\n"
        "      Plotly.setPlotConfig({locale: 'zh-cn'});\n"
        "    }\n"
        "  })();\n"
        "</script>\n"
        "<script>\n"
        "  // 强制把“下载图片”按钮 tooltip 改为中文（该按钮在部分版本/环境下不会随 locale 翻译）\n"
        "  (function(){\n"
        "    function patchDownloadTooltip(){\n"
        "      try {\n"
        "        var btn = document.querySelector('.modebar-btn[data-title=\"Download plot as a png\"]')\n"
        "          || document.querySelector('.modebar-btn[data-title=\"Download plot as a PNG\"]');\n"
        "        if (!btn) return false;\n"
        "        var cn = '下载为PNG图片';\n"
        "        btn.setAttribute('data-title', cn);\n"
        "        btn.setAttribute('title', cn);\n"
        "        btn.setAttribute('aria-label', cn);\n"
        "        return true;\n"
        "      } catch (e) { return false; }\n"
        "    }\n"
        "\n"
        "    // 等待 modebar 渲染出来再替换（最多重试 60 次，大约 3 秒）\n"
        "    var tries = 0;\n"
        "    var timer = setInterval(function(){\n"
        "      tries += 1;\n"
        "      if (patchDownloadTooltip() || tries >= 60) {\n"
        "        clearInterval(timer);\n"
        "      }\n"
        "    }, 50);\n"
        "  })();\n"
        "</script>\n"
    )
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", zh_locale_inject + "</head>")

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n✓ HTML文件已生成: {output_html}")
    return output_html


def main(n_years=5):
    excel_file = "output/黄金（Au99.99）.xlsx"
    sheet_name = 0  # 若有多个 sheet，请调整
    try:
        output_file = plot_gold_close_price(excel_file, sheet_name, n_years)
        print(f"\n完成！HTML文件已保存到: {output_file}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main(n_years=10)