import lottery2excel as lex
import lottery_numerical_analysis as lna
import lottery_chart_plotting as lcp
import au99992excel as auex
import au9999_chart_plotting as aucp
import bosera_gold_etf2excel as bgex
import bosera_gold_etf_chart_plotting as bgecp
import bosera_gold_au9999_chart_plotting as bgacp
import stock2excel as sex
import stock_chart_plotting as scp
import more_stocks_chart_plotting as mscp

if __name__ == "__main__":
    # 获取彩票中奖号码数据
    lex.main()
    # 彩票中奖号码分析
    lna.main()
    # 彩票中奖号码数字规律可视化
    lcp.main()
    # 黄金（9999）近10年数据
    auex.main(n_years=10)
    # 生成近10年黄金（9999）图表
    aucp.main(n_years=10)
    # 获取博时黄金ETF数据
    bgex.main(n_years=10)
    # 生成博时黄金ETF图表
    bgecp.main(n_years=10)
    # 生成博时黄金和黄金（9999）走势对比数据
    bgacp.main(n_years=10)
    # 获取股票数据
    sex.main(n_years=10)
    # 生成股票图表
    scp.main(n_years=10)
    # 生成更多股票图表（收盘价对比、涨跌幅对比）
    mscp.main(n_years=10)
    