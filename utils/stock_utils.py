import re
import requests
import logging
import json

logger = logging.getLogger(__name__)

class StockCodeLookup:
    @staticmethod
    def get_stock_info(stock_code):
        """
        根据股票代码获取股票信息
        支持A股（沪市、深市）、港股、美股
        返回纯字典对象，确保所有值都可JSON序列化
        """
        try:
            # 确保stock_code是字符串类型
            stock_code = str(stock_code)
            logger.info(f'开始查询股票代码: {stock_code}')
            
            api_url, market = StockCodeLookup._get_api_url_and_market(stock_code)
            
            if not api_url:
                # 返回标准格式的字典，所有值都是基本数据类型
                return {
                    'success': False,
                    'message': '不支持的股票代码格式',
                    'data': None
                }
            
            logger.info(f'使用API URL: {api_url}')
            # 调用API获取数据
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            
            # 解析返回的数据
            data = response.text
            logger.info(f'API返回数据长度: {len(data)} 字符')
            
            if data and '"' in data:
                match = re.search(r'"([^"]+)', data)
                if match and match.group(1):
                    # 确保所有返回值都是字符串或基本类型
                    stock_name = str(match.group(1).split(',')[0])
                    market_str = str(market)
                    
                    return {
                        'success': True,
                        'data': {
                            'code': stock_code,
                            'name': stock_name,
                            'market': market_str
                        }
                    }
            
            # 如果无法从API获取，返回失败
            return {
                'success': False,
                'message': '无法获取股票信息',
                'data': None
            }
        
        except requests.exceptions.RequestException as e:
            # 确保错误信息是字符串
            error_msg = str(e)
            logger.error(f'获取股票信息网络错误: {error_msg}')
            return {
                'success': False,
                'message': '获取股票信息时发生网络错误',
                'error': error_msg
            }
        except Exception as e:
            # 确保错误信息是字符串
            error_msg = str(e)
            logger.error(f'获取股票信息异常: {error_msg}')
            return {
                'success': False,
                'message': '获取股票信息时发生错误',
                'error': error_msg
            }
    
    @staticmethod
    def _get_api_url_and_market(stock_code):
        """根据股票代码格式确定API URL和市场类型"""
        # 1. 沪市股票：6开头的6位数
        if stock_code.startswith('6') and len(stock_code) == 6:
            return f'http://hq.sinajs.cn/list=sh{stock_code}', 'sh'
        
        # 2. 深市股票：0或3开头的6位数
        elif (stock_code.startswith('0') or stock_code.startswith('3')) and len(stock_code) == 6:
            return f'http://hq.sinajs.cn/list=sz{stock_code}', 'sz'
        
        # 3. 港股股票：0开头的5位数或带有.hk后缀
        elif (stock_code.startswith('0') and len(stock_code) == 5) or '.hk' in stock_code:
            hk_code = stock_code.split('.')[0] if '.hk' in stock_code else stock_code
            return f'http://hq.sinajs.cn/list=hk{hk_code}', 'hk'
        
        # 4. 美股股票：通常是字母代码，可能带有.NYSE/.NASDAQ/.AMEX等后缀
        elif re.match(r'^[A-Za-z]{1,5}(-[A-Za-z]{1,2})?(\.[A-Za-z]+)?$', stock_code):
            us_code = stock_code.split('.')[0].upper() if '.' in stock_code else stock_code.upper()
            return f'http://hq.sinajs.cn/list={us_code}', 'us'
        
        # 不支持的格式
        return None, None
    
    @staticmethod
    def validate_stock_code(stock_code):
        """验证股票代码格式是否有效"""
        # A股：6位数字
        if re.match(r'^[036]\d{5}$', stock_code):
            return True
        # 港股：5位数字或带有.hk后缀
        elif re.match(r'^0\d{4}$', stock_code) or re.match(r'^[0-9]{1,5}\.hk$', stock_code, re.IGNORECASE):
            return True
        # 美股：字母代码
        elif re.match(r'^[A-Za-z]{1,5}(-[A-Za-z]{1,2})?(\.[A-Za-z]+)?$', stock_code):
            return True
        return False