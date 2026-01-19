import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os


def plot_stock_chart(excel_file: str, sheet_name: str = "上证综合指数", years: int = 3, 
                     output_html: str = None):
    """
    绘制股票收盘价折线图，支持交互式缩放和鼠标悬停显示坐标，输出为HTML5格式
    
    Args:
        excel_file: Excel文件路径
        sheet_name: Sheet名称
        years: 显示近N年的数据
        output_html: 输出的HTML文件路径，如果为None则使用默认路径
    """
    # 读取Excel数据
    print(f"正在读取Excel文件: {excel_file}")
    print(f"Sheet名称: {sheet_name}")
    df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
    
    # 检查必要的列是否存在
    if '日期Date' not in df.columns or '收盘Close' not in df.columns:
        raise ValueError(f"Excel文件中缺少必要的列。现有列: {df.columns.tolist()}")
    
    # 转换日期格式（从YYYYMMDD整数转换为datetime）
    df['日期'] = pd.to_datetime(df['日期Date'].astype(str), format='%Y%m%d')
    
    # 筛选近N年的数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    df_filtered = df[df['日期'] >= start_date].copy()
    
    if df_filtered.empty:
        raise ValueError(f"筛选后没有数据。请检查日期范围。")
    # 计算当前可用数据跨度（年），用于动态增加时间范围按钮
    available_years = (df_filtered['日期'].max() - df_filtered['日期'].min()).days / 365.25
    
    # 按日期排序
    df_filtered = df_filtered.sort_values('日期')
    
    print(f"筛选后数据量: {len(df_filtered)} 条")
    print(f"日期范围: {df_filtered['日期'].min()} 至 {df_filtered['日期'].max()}")
    
    # 创建plotly图表
    fig = go.Figure()
    
    # 添加折线图
    fig.add_trace(go.Scatter(
        x=df_filtered['日期'],
        y=df_filtered['收盘Close'],
        mode='lines',
        name='收盘价',
        line=dict(color='#1f77b4', width=2),
        hovertemplate='<b>日期</b>: %{x|%Y-%m-%d}<br>' +
                      '<b>收盘价</b>: %{y:.2f}<br>' +
                      '<extra></extra>',
    ))
    
    # 设置图表布局
    fig.update_layout(
        title={
            'text': f'{sheet_name} - 近{years}年收盘价走势图',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'family': 'Arial, sans-serif'}
        },
        xaxis=dict(
            title=dict(text='日期', font=dict(size=14)),
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            tickformat='%Y-%m-%d',
            dtick="M1",  # 每月显示一个刻度
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
            type="date"
        ),
        yaxis=dict(
            title=dict(text='收盘价', font=dict(size=14)),
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        hovermode='x unified',  # 鼠标悬停时显示统一的x轴信息
        template='plotly_white',
        height=700,
        margin=dict(l=60, r=30, t=80, b=60),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        )
    )
    
    # 设置输出文件路径
    if output_html is None:
        # 使用Excel文件所在目录，文件名基于sheet名称
        excel_dir = os.path.dirname(excel_file)
        if not excel_dir:
            excel_dir = os.getcwd()
        output_html = os.path.join(excel_dir, f"{sheet_name}_近{years}年收盘价走势图.html")
    
    # 保存为HTML文件
    print(f"\n正在生成HTML文件: {output_html}")
    
    # 配置工具栏（Plotly 的工具栏 tooltip 语言由 locale 决定）
    # 注意：Plotly 常用 locale key 是 'zh-cn'（小写、连字符），且需要额外加载 locale 脚本才会生效
    config = {
        'locale': 'zh-cn',
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToAdd': [],
        'modeBarButtonsToRemove': [],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'{sheet_name}_近{years}年收盘价走势图',
            'height': 700,
            'width': 1400,
            'scale': 1
        }
    }
    
    # 生成 HTML（先输出完整 HTML，便于注入中文 locale 脚本）
    html_content = fig.to_html(include_plotlyjs='cdn', config=config, full_html=True)

    # 注入 Plotly 官方中文 locale，并强制全局使用中文
    # 说明：仅设置 config['locale'] 不够；plotly.js CDN 默认不一定内置 zh-cn，需要单独加载 locale 文件
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
    
    # 依赖 Plotly zh-cn locale 来处理月份/tooltip 文案，避免对 HTML 进行字符串替换，
    # 防止破坏 Plotly 内嵌的二进制数据（大数据量时替换可能导致 TypedArray 长度异常）
    # 工具栏 tooltip 文案由 Plotly 的 zh-cn locale 控制；不再用字符串替换的方式“硬改”，避免漏改/误改
    
    # 写入文件
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ HTML文件已生成: {output_html}")
    print("\n交互功能说明：")
    print("  - 鼠标悬停：自动显示当前点的日期和收盘价")
    print("  - 缩放：")
    print("    * 拖拽选择区域进行缩放")
    print("    * 双击图表重置缩放")
    print("    * 使用鼠标滚轮进行缩放")
    print("    * 使用工具栏的缩放工具")
    print("  - 平移：点击并拖拽图表进行平移")
    print("  - 时间范围选择器：使用图表上方的按钮快速选择时间范围")
    print("  - 范围滑块：使用图表下方的滑块快速定位到特定时间段")
    print("  - 工具栏：右上角工具栏提供更多交互功能（下载图片、缩放、平移等）")
    print("\n提示：可以直接在浏览器中打开HTML文件查看和分享")
    
    return output_html


if __name__ == "__main__":
    excel_file = "/Users/chenzhangjie/Downloads/股票指数数据.xlsx"
    sheet_name = "上证综合指数"
    years = 10
    
    try:
        output_file = plot_stock_chart(excel_file, sheet_name, years)
        print(f"\n完成！HTML文件已保存到: {output_file}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
