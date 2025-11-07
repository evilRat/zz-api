from flask import request
from flask_restful import Resource
import logging
from utils.stock_utils import StockCodeLookup as StockLookupUtil

logger = logging.getLogger(__name__)

class StockCodeLookupResource(Resource):
    def post(self):
        """处理股票代码查询请求"""
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'message': '请求数据不能为空'
                }, 400
            
            stock_code = data.get('stockCode')
            if not stock_code:
                return {
                    'success': False,
                    'message': '缺少stockCode参数'
                }, 400
            
            # 调用股票查询工具
            result = StockLookupUtil.get_stock_info(stock_code)
            
            if result['success']:
                return result
            else:
                # 根据错误信息返回不同的状态码
                if '不支持的股票代码格式' in result.get('message', ''):
                    return result, 400
                elif '无法获取股票信息' in result.get('message', ''):
                    return result, 404
                else:
                    return result, 500
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f'股票代码查询失败: {error_msg}')
            return {
                'success': False,
                'message': '查询失败',
                'error': error_msg
            }, 500
    
    def get(self):
        """支持GET请求，方便测试"""
        try:
            stock_code = request.args.get('stockCode')
            if not stock_code:
                return {
                    'success': False,
                    'message': '缺少stockCode参数'
                }, 400
            
            # 调用股票查询工具
            result = StockLookupUtil.get_stock_info(stock_code)
            
            if result['success']:
                return result
            else:
                if '不支持的股票代码格式' in result.get('message', ''):
                    return result, 400
                elif '无法获取股票信息' in result.get('message', ''):
                    return result, 404
                else:
                    return result, 500
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f'股票代码查询失败: {error_msg}')
            return {
                'success': False,
                'message': '查询失败',
                'error': error_msg
            }, 500