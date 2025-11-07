from flask import request, jsonify
from flask_restful import Resource
import logging
from utils.db import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

class TradeOperations(Resource):
    def post(self):
        """处理交易操作请求"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据不能为空'
                }), 400
            
            operation = data.get('operation')
            operation_data = data.get('data', {})
            
            # 模拟微信小程序的openid（实际项目中需要从认证中获取）
            openid = request.headers.get('X-OpenID', 'test_openid')
            
            if operation == 'getAllTrades':
                return self._get_all_trades(operation_data, openid)
            elif operation == 'addTrade':
                return self._add_trade(operation_data, openid)
            elif operation == 'deleteTrade':
                return self._delete_trade(operation_data, openid)
            elif operation == 'getTradeById':
                return self._get_trade_by_id(operation_data, openid)
            else:
                return jsonify({
                    'success': False,
                    'message': '不支持的操作类型'
                }), 400
        
        except Exception as e:
            logger.error(f'交易操作失败: {str(e)}')
            return jsonify({
                'success': False,
                'message': '操作失败',
                'error': str(e)
            }), 500
    
    def _get_all_trades(self, data, openid):
        """获取所有交易记录 - 支持分页和筛选"""
        try:
            db = get_db()
            page = data.get('page', 1)
            page_size = data.get('pageSize', 20)
            match_status = data.get('matchStatus')
            stock_code = data.get('stockCode')
            type = data.get('type')
            
            skip = (page - 1) * page_size
            
            # 构建查询条件
            query = {'_openid': openid}
            
            if match_status and match_status != 'all':
                query['matchStatus'] = match_status
            
            if stock_code and stock_code != 'all':
                query['stockCode'] = stock_code
            
            if type and type != 'all':
                query['type'] = type
            
            # 执行分页查询
            trades = list(db.trades.find(query)
                         .sort('date', -1)
                         .skip(skip)
                         .limit(page_size))
            
            # 获取总数
            total = db.trades.count_documents(query)
            
            # 将ObjectId转换为字符串
            for trade in trades:
                trade['_id'] = str(trade['_id'])
            
            return jsonify({
                'success': True,
                'data': trades,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'total': total,
                    'hasMore': skip + len(trades) < total
                }
            })
        
        except Exception as e:
            logger.error(f'获取交易记录失败: {str(e)}')
            raise
    
    def _add_trade(self, data, openid):
        """添加新交易记录"""
        try:
            db = get_db()
            
            # 验证必要字段
            required_fields = ['date', 'stockCode', 'stockName', 'type', 'price', 'quantity']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'success': False,
                        'message': f'缺少必要字段: {field}'
                    }), 400
            
            # 准备插入数据
            trade_data = {
                **data,
                '_openid': openid,
                'matchStatus': 'unmatched',  # 默认状态为未匹配
                'createTime': datetime.utcnow(),
                'updateTime': datetime.utcnow()
            }
            
            # 插入数据
            result = db.trades.insert_one(trade_data)
            
            return jsonify({
                'success': True,
                'data': {
                    'inserted_id': str(result.inserted_id)
                }
            })
        
        except Exception as e:
            logger.error(f'添加交易记录失败: {str(e)}')
            raise
    
    def _delete_trade(self, data, openid):
        """删除交易记录"""
        try:
            db = get_db()
            trade_id = data.get('tradeId')
            
            if not trade_id:
                return jsonify({
                    'success': False,
                    'message': '缺少tradeId参数'
                }), 400
            
            # 执行删除
            result = db.trades.delete_one({
                '_id': trade_id,
                '_openid': openid
            })
            
            if result.deleted_count == 0:
                return jsonify({
                    'success': False,
                    'message': '交易记录不存在或无权限删除'
                }), 404
            
            return jsonify({
                'success': True,
                'data': {
                    'deleted_count': result.deleted_count
                }
            })
        
        except Exception as e:
            logger.error(f'删除交易记录失败: {str(e)}')
            raise
    
    def _get_trade_by_id(self, data, openid):
        """根据ID获取交易记录"""
        try:
            db = get_db()
            trade_id = data.get('tradeId')
            
            if not trade_id:
                return jsonify({
                    'success': False,
                    'message': '缺少tradeId参数'
                }), 400
            
            # 查询记录
            trade = db.trades.find_one({
                '_id': trade_id,
                '_openid': openid
            })
            
            if not trade:
                return jsonify({
                    'success': False,
                    'message': '交易记录不存在'
                }), 404
            
            # 将ObjectId转换为字符串
            trade['_id'] = str(trade['_id'])
            
            return jsonify({
                'success': True,
                'data': trade
            })
        
        except Exception as e:
            logger.error(f'获取交易记录失败: {str(e)}')
            raise