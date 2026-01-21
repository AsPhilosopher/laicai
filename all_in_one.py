import lottery2excel as lex
import lottery_numerical_analysis as lna
import au99992excel as auex
import au9999_chart_plotting as aucp
import stock2excel as sex
import stock_chart_plotting as scp
import more_stocks_chart_plotting as mscp

if __name__ == "__main__":
    # 彩票中奖号码数据
    lex.main()
    # 彩票中奖号码分析
    lna.main()
    # 黄金近10年数据
    auex.main(n_years=10)
    # 生成近10年黄金图表
    aucp.main(n_years=10)
    # 生成股票数据
    sex.main(n_years=10)
    # 生成股票图表
    scp.main(n_years=10)
    # 生成更多股票图表
    mscp.main(n_years=10)
    