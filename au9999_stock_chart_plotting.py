import os
from datetime import datetime, timedelta
from typing import Optional

import plotly.graph_objects as go

from more_stocks_chart_plotting import _load_sheet_series
from bosera_gold_au9999_chart_plotting import _load_au9999_change


def plot_sh_index_vs_au9999(
    stock_excel: str,
    au9999_excel: str,
    stock_sheet: str = "上证综合指数",
    au9999_sheet: str = "黄金数据",
    years: int = 10,
    output_html: Optional[str] = None,
):
    """
    将上证综合指数收盘价与黄金（Au99.99）收盘价绘制到同一张折线图（Plotly），输出为 HTML 文件。

    参数:
        stock_excel: 股票指数 Excel 路径（如 output/股票指数数据.xlsx）
        au9999_excel: 黄金 Au99.99 Excel 路径（如 output/黄金（Au99.99）.xlsx）
        stock_sheet: 股票指数所在 sheet 名称（默认“上证综合指数”）
        au9999_sheet: Au99.99 数据所在 sheet 名称（默认“黄金数据”）
        years: 显示最近 N 年数据
        output_html: 输出 HTML 文件路径；为 None 时自动生成到 Excel 同目录
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    # 读取上证综合指数“涨跌幅(%)”
    print(f"正在读取上证综合指数涨跌幅: {stock_excel} (sheet={stock_sheet})")
    df_stock = _load_sheet_series(stock_excel, stock_sheet, value_type="change")
    df_stock = df_stock[df_stock["日期"] >= start_date].sort_values("日期")

    # 直接读取 Au99.99 的涨跌幅列：Up/Down(%)(涨跌(%))
    print(f"正在读取黄金(Au99.99)涨跌幅: {au9999_excel} (sheet={au9999_sheet})")
    df_gold = _load_au9999_change(au9999_excel, sheet_name=au9999_sheet)
    df_gold = df_gold[df_gold["日期"] >= start_date].sort_values("日期")

    if df_stock.empty:
        raise ValueError(f"上证综合指数在近{years}年范围内无有效涨跌幅数据，请检查数据/年份范围。")
    if df_gold.empty:
        raise ValueError(f"黄金(Au99.99)在近{years}年范围内无有效涨跌幅数据，请检查数据/年份范围。")

    # 计算整体日期跨度，用于时间范围选择器
    min_date = min(df_stock["日期"].min(), df_gold["日期"].min())
    max_date = max(df_stock["日期"].max(), df_gold["日期"].max())
    available_years = (max_date - min_date).days / 365.25

    fig = go.Figure()

    # 上证综合指数 涨跌幅(%)
    fig.add_trace(
        go.Scatter(
            x=df_stock["日期"],
            y=df_stock["数值"],
            mode="lines",
            name="上证综合指数 涨跌幅(%)",
            line=dict(color="#1f77b4", width=2.5),
            hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br>"
            "<b>上证综合指数 涨跌幅</b>: %{y:.2f}%<br>"
            "<extra></extra>",
        )
    )

    # 黄金 Au99.99 涨跌幅(%)
    fig.add_trace(
        go.Scatter(
            x=df_gold["日期"],
            y=df_gold["数值"],
            mode="lines",
            name="黄金(Au99.99) 涨跌幅(%)",
            line=dict(color="#FFD700", width=2.5),
            hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br>"
            "<b>黄金(Au99.99) 涨跌幅</b>: %{y:.2f}%<br>"
            "<extra></extra>",
        )
    )

    fig.update_layout(
        title={
            "text": f"上证综合指数 vs 黄金(Au99.99) - 近{years}年涨跌幅走势图",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Arial, sans-serif"},
        },
        xaxis=dict(
            title=dict(text="日期", font=dict(size=14)),
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            tickformat="%Y-%m-%d",
            dtick="M1",
            rangeselector=dict(
                buttons=(lambda span_years: (
                    [
                        dict(count=1, label="1个月", step="month", stepmode="backward"),
                        dict(count=3, label="3个月", step="month", stepmode="backward"),
                        dict(count=6, label="6个月", step="month", stepmode="backward"),
                        dict(count=1, label="1年", step="year", stepmode="backward"),
                    ]
                    + ([dict(count=3, label="3年", step="year", stepmode="backward")] if span_years > 3 else [])
                    + ([dict(count=5, label="5年", step="year", stepmode="backward")] if span_years > 5 else [])
                    + [dict(step="all", label="全部")]
                ))(available_years)
            ),
            rangeslider=dict(visible=True, thickness=0.05),
            type="date",
        ),
        yaxis=dict(
            title=dict(text="涨跌幅(%)", font=dict(size=14)),
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
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
            borderwidth=1,
        ),
    )

    if output_html is None:
        # 默认输出到股票 Excel 所在目录
        out_dir = os.path.dirname(stock_excel) or os.getcwd()
        output_html = os.path.join(
            out_dir, f"黄金Au99.99_上证综合指数_近{years}年涨跌幅走势图.html"
        )

    print(f"\n正在生成HTML文件: {output_html}")
    config = {
        "locale": "zh-cn",
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToAdd": [],
        "modeBarButtonsToRemove": [],
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"黄金Au99.99_上证综合指数_近{years}年涨跌幅走势图",
            "height": 700,
            "width": 1400,
            "scale": 1,
        },
    }

    html_content = fig.to_html(include_plotlyjs="cdn", config=config, full_html=True)

    # 注入 Plotly 中文语言包，并强制全局使用中文，同时修正“下载图片”按钮的英文 tooltip
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

    try:
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_content)
    except PermissionError:
        fallback_dir = os.getcwd()
        fallback_path = os.path.join(fallback_dir, os.path.basename(output_html))
        print(f"警告: 无法写入 {output_html}，将改为写入: {fallback_path}")
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        output_html = fallback_path

    print(f"\n✓ HTML文件已生成: {output_html}")
    return output_html


def main(n_years: int = 10):
    """
    默认从项目根目录下的 output/ 中读取：
    - 股票指数数据.xlsx（上证综合指数）
    - 黄金（Au99.99）.xlsx（黄金收盘价）
    """
    project_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(project_dir, "output")

    stock_excel = os.path.join(base_dir, "股票指数数据.xlsx")
    au9999_excel = os.path.join(base_dir, "黄金（Au99.99）.xlsx")

    out = plot_sh_index_vs_au9999(
        stock_excel=stock_excel,
        au9999_excel=au9999_excel,
        stock_sheet="上证综合指数",
        au9999_sheet="黄金数据",
        years=n_years,
    )
    print(f"\n完成！HTML文件已保存到: {out}")


if __name__ == "__main__":
    main(n_years=10)

