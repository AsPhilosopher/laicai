import requests
import json
from typing import List, Dict, Any
from datetime import datetime


class LotteryScraper:
    """中国福利彩票双色球开奖信息爬虫"""
    
    def __init__(self):
        self.api_url = "http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def get_lottery_data(
        self,
        page_no: int = 1,
        page_size: int = 30,
        issue_start: str = "",
        issue_end: str = "",
        day_start: str = "",
        day_end: str = ""
    ) -> List[Dict[str, Any]]:
        """获取双色球开奖数据
        
        Args:
            page_no: 页码，从1开始
            page_size: 每页条数，最大100
            issue_start: 起始期号（格式：2024001）
            issue_end: 结束期号
            day_start: 起始日期（格式：2024-01-01）
            day_end: 结束日期
        
        Returns:
            开奖信息列表
        """
        params = {
            "name": "ssq",  # 双色球
            "issueCount": "",
            "issueStart": issue_start,
            "issueEnd": issue_end,
            "dayStart": day_start,
            "dayEnd": day_end,
            "pageNo": page_no,
            "pageSize": page_size,
            "week": "",
            "systemType": "PC"
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("state") == 0 and data.get("result"):
                return data["result"]
            else:
                print(f"API返回异常: {data.get('message', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return []
    
    def parse_lottery_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """解析单条开奖信息"""
        # 解析红球号码
        red_balls = []
        if item.get("red"):
            red_balls = item["red"].split(",")
        
        # 解析蓝球号码
        blue_ball = item.get("blue", "")
        
        return {
            "期号": item.get("code", ""),
            "开奖日期": item.get("date", ""),
            "红球": red_balls,
            "蓝球": blue_ball,
            "销售金额": item.get("sales", ""),
            "奖池金额": item.get("poolmoney", ""),
            "一等奖注数": item.get("content", ""),
            "详情链接": item.get("detailsLink", "")
        }
    
    def get_recent_lotteries(self, count: int = 30) -> List[Dict[str, Any]]:
        """获取最近N期的开奖信息"""
        all_results = []
        page_no = 1
        page_size = min(count, 100)  # 每页最多100条
        
        while len(all_results) < count:
            data = self.get_lottery_data(page_no=page_no, page_size=page_size)
            if not data:
                break
            
            for item in data:
                if len(all_results) >= count:
                    break
                parsed = self.parse_lottery_info(item)
                all_results.append(parsed)
            
            # 如果返回的数据少于page_size，说明已经到底了
            if len(data) < page_size:
                break
                
            page_no += 1
        
        return all_results
    
    def print_lottery_info(self, lotteries: List[Dict[str, Any]]):
        """打印开奖信息"""
        print(f"\n{'='*80}")
        print(f"共获取 {len(lotteries)} 期开奖信息")
        print(f"{'='*80}\n")
        
        for i, lottery in enumerate(lotteries, 1):
            print(f"【第 {i} 期】")
            print(f"期号: {lottery['期号']}")
            print(f"开奖日期: {lottery['开奖日期']}")
            print(f"红球: {', '.join(lottery['红球'])}")
            print(f"蓝球: {lottery['蓝球']}")
            if lottery.get('销售金额'):
                print(f"销售金额: {lottery['销售金额']}")
            print("-" * 80)


if __name__ == "__main__":
    scraper = LotteryScraper()
    
    # 示例1: 获取最近30期开奖信息
    print("正在获取最近30期开奖信息...")
    recent_lotteries = scraper.get_recent_lotteries(count=30)
    scraper.print_lottery_info(recent_lotteries)
    
    # 示例2: 按日期范围查询
    print("\n\n按日期范围查询（2024年1月）...")
    date_lotteries = scraper.get_lottery_data(
        day_start="2024-01-01",
        day_end="2024-01-31",
        page_size=100
    )
    parsed_date_lotteries = [scraper.parse_lottery_info(item) for item in date_lotteries]
    scraper.print_lottery_info(parsed_date_lotteries)
    
    # 示例3: 保存为JSON文件
    import json
    with open("lottery_data.json", "w", encoding="utf-8") as f:
        json.dump(recent_lotteries, f, ensure_ascii=False, indent=2)
    print("\n数据已保存到 lottery_data.json")