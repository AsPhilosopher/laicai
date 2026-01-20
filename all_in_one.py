import au99992excel as auex
import au9999_chart_plotting as aucp
import stock2excel as sex
import stock_chart_plotting as scp
import more_stocks_chart_plotting as mscp

if __name__ == "__main__":
    # 黄金近10年数据
    auex.main(n_years=10)
    # 生成黄金图表
    aucp.main()
    # 生成股票数据
    sex.main()
    # 生成股票图表
    scp.main()
    # 生成更多股票图表
    mscp.main()
    