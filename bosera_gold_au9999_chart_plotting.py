import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import plotly.graph_objects as go


def _load_au9999_close(excel_file: str, sheet_name: str = "黄金数据") -> pd.DataFrame:
    """
    读取 Au99.99 收盘价序列，输出两列：
    - 日期: datetime64[ns]
    - 数值: float (Close 收盘价)
    """
    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")

    date_col = "Date(日期)"
    value_col = "Close(收盘价)"
    if date_col not in df.columns:
        raise ValueError(f"[{sheet_name}] 找不到日期列: {date_col}，当前列: {df.columns.tolist()}")
    if value_col not in df.columns:
        raise ValueError(f"[{sheet_name}] 找不到收盘价列: {value_col}，当前列: {df.columns.tolist()}")

    out = pd.DataFrame(
        {
            "日期": pd.to_datetime(df[date_col], errors="coerce"),
            "数值": pd.to_numeric(df[value_col], errors="coerce"),
        }
    ).dropna(subset=["日期", "数值"])
    return out


def _load_bosera_etf_nav_x70(excel_file: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
    """
    读取博时黄金ETF 单位净值(元) 并乘以 70，输出两列：
    - 日期: datetime64[ns]
    - 数值: float (单位净值 * 70)
    """
    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")

    date_col = "日期"
    nav_col = "单位净值(元)"
    if date_col not in df.columns:
        raise ValueError(f"[{sheet_name}] 找不到日期列: {date_col}，当前列: {df.columns.tolist()}")
    if nav_col not in df.columns:
        raise ValueError(f"[{sheet_name}] 找不到单位净值列: {nav_col}，当前列: {df.columns.tolist()}")

    nav = pd.to_numeric(df[nav_col], errors="coerce") * 70.0
    out = pd.DataFrame(
        {
            "日期": pd.to_datetime(df[date_col], errors="coerce"),
            "数值": nav,
        }
    ).dropna(subset=["日期", "数值"])
    return out


def plot_au9999_vs_bosera_etf(
    au9999_excel: str,
    bosera_etf_excel: str,
    years: int = 10,
    output_html: Optional[str] = None,
):
    """
    将黄金（Au99.99）收盘价与（博时黄金ETF单位净值*70）绘制到同一个折线图（Plotly），输出 HTML。
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)

    print(f"正在读取 Au99.99: {au9999_excel}")
    df_gold = _load_au9999_close(au9999_excel)
    df_gold = df_gold[df_gold["日期"] >= start_date].sort_values("日期")

    print(f"正在读取 博时黄金ETF: {bosera_etf_excel}")
    df_etf = _load_bosera_etf_nav_x70(bosera_etf_excel)
    df_etf = df_etf[df_etf["日期"] >= start_date].sort_values("日期")

    if df_gold.empty:
        raise ValueError(f"Au99.99 在近{years}年范围内无有效数据，请检查数据/年份范围。")
    if df_etf.empty:
        raise ValueError(f"博时黄金ETF 在近{years}年范围内无有效数据，请检查数据/年份范围。")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_gold["日期"],
            y=df_gold["数值"],
            mode="lines",
            name="黄金(Au99.99) 收盘价",
            line=dict(color="#FFD700", width=2.5),
            hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br>"
            "<b>Au99.99 收盘价</b>: %{y:.2f}<br>"
            "<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_etf["日期"],
            y=df_etf["数值"],
            mode="lines",
            name="博时黄金ETF 单位净值×70",
            line=dict(color="#1f77b4", width=2.5),
            hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br>"
            "<b>ETF 单位净值×70</b>: %{y:.2f}<br>"
            "<extra></extra>",
        )
    )

    min_date = min(df_gold["日期"].min(), df_etf["日期"].min())
    max_date = max(df_gold["日期"].max(), df_etf["日期"].max())
    available_years = (max_date - min_date).days / 365.25

    fig.update_layout(
        title={
            "text": f"黄金(Au99.99) 收盘价 vs 博时黄金ETF(单位净值×70) - 近{years}年",
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
            title=dict(text="价格/净值(×70)", font=dict(size=14)),
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
        out_dir = os.path.dirname(au9999_excel) or os.getcwd()
        output_html = os.path.join(out_dir, f"黄金Au99.99_博时黄金ETFx70_近{years}年对比走势图.html")

    print(f"\n正在生成HTML文件: {output_html}")
    config = {
        "locale": "zh-cn",
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"黄金Au99.99_博时黄金ETFx70_近{years}年对比走势图",
            "height": 700,
            "width": 1400,
            "scale": 1,
        },
    }

    html_content = fig.to_html(include_plotlyjs="cdn", config=config, full_html=True)

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


def main(n_years=5):
    # 使用相对路径：以当前脚本所在目录为基准定位到项目的 output/ 目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(project_dir, "output")
    au9999_excel = os.path.join(base_dir, "黄金（Au99.99）.xlsx")
    bosera_etf_excel = os.path.join(base_dir, "博时黄金ETF数据.xlsx")

    out = plot_au9999_vs_bosera_etf(au9999_excel, bosera_etf_excel, years=n_years)
    print(f"\n完成！HTML文件已保存到: {out}")


if __name__ == "__main__":
    main(n_years=10)
