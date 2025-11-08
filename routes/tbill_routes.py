from flask.wrappers import Response


from typing import Any, Literal


from flask import request, jsonify
from flask_restful import Resource
import logging
from utils.db import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

class TBillOperations(Resource):
    def post(self):
        """处理T账单操作请求"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '请求数据不能为空'
                }), 400
            
            operation = data.get('operation')
            operation_data = data.get('data', {})
            
            # 从参数中获取微信小程序的openid（实际项目中需要从认证中获取）
            openid = data.get('openId', 'test_openid')
            
            if operation == 'createTBill':
                return self._create_tbill(operation_data, openid)
            elif operation == 'updateTBill':
                return self._update_tbill(operation_data, openid)
            elif operation == 'getTBillById':
                return self._get_tbill_detail(operation_data, openid)
            elif operation == 'getAllTBills':
                return self._get_all_tbills(operation_data, openid)
            else:
                return jsonify({
                    'success': False,
                    'message': '不支持的操作类型'
                }), 400
        
        except Exception as e:
            logger.error(f'T账单操作失败: {str(e)}')
            return jsonify({
                'success': False,
                'message': '操作失败',
                'error': str(e)
            }), 500
    
    def _create_tbill(self, data, openid):
        """创建T账单，使用事务确保数据一致性"""
        try:
            db = get_db()
            openId = data.get('openId')
            date = data.get('date')
            
            # 参数验证
            if not all([openId, date]):
                return jsonify({
                    'success': False,
                    'message': '缺少必要参数：openId, date'
                }), 400
            
            # 开始事务（MongoDB 4.0+支持事务）
            with db.client.start_session() as session:
                with session.start_transaction():
                    try:
                        # 1. 获取A和B交易记录
                        a_trade = db.trades.find_one(
                            {'_id': a_trade_id, '_openid': openid},
                            session=session
                        )
                        b_trade = db.trades.find_one(
                            {'_id': b_trade_id, '_openid': openid},
                            session=session
                        )
                        
                        if not a_trade or not b_trade:
                            session.abort_transaction()
                            return jsonify({
                                'success': False,
                                'message': '交易记录不存在'
                            }), 404
                        
                        # 2. 验证交易记录状态和匹配条件
                        if a_trade.get('matchStatus') != 'unmatched' or b_trade.get('matchStatus') != 'unmatched':
                            session.abort_transaction()
                            return jsonify({
                                'success': False,
                                'message': '交易记录已匹配，无法创建T账单'
                            }), 400
                        
                        # 验证股票代码一致性
                        if a_trade.get('stockCode') != b_trade.get('stockCode'):
                            session.abort_transaction()
                            return jsonify({
                                'success': False,
                                'message': 'A和B交易记录的股票代码不一致'
                            }), 400
                        
                        # 3. 计算盈利金额和盈利率
                        # 假设A是买入，B是卖出
                        profit = b_trade.get('price') - a_trade.get('price')
                        profit_rate = (profit / a_trade.get('price')) * 100 if a_trade.get('price') > 0 else 0
                        
                        # 4. 创建T账单记录
                        tbill_data = {
                            'aTradeId': a_trade_id,
                            'bTradeId': b_trade_id,
                            'stockCode': a_trade.get('stockCode'),
                            'stockName': a_trade.get('stockName'),
                            'stockMarket': a_trade.get('stockMarket', 'unknown'),
                            'buyPrice': a_trade.get('price'),
                            'sellPrice': b_trade.get('price'),
                            'quantity': min(a_trade.get('quantity', 0), b_trade.get('quantity', 0)),
                            'profit': profit,
                            'profitRate': profit_rate,
                            'date': date,
                            '_openid': openid,
                            'createTime': datetime.utcnow(),
                            'updateTime': datetime.utcnow()
                        }
                        
                        tbill_result = db.tbills.insert_one(tbill_data, session=session)
                        
                        # 5. 更新交易记录状态
                        db.trades.update_one(
                            {'_id': a_trade_id, '_openid': openid},
                            {'$set': {'matchStatus': 'matched', 'updateTime': datetime.utcnow()}},
                            session=session
                        )
                        
                        db.trades.update_one(
                            {'_id': b_trade_id, '_openid': openid},
                            {'$set': {'matchStatus': 'matched', 'updateTime': datetime.utcnow()}},
                            session=session
                        )
                        
                        # 提交事务
                        session.commit_transaction()
                        
                        return jsonify({
                            'success': True,
                            'data': {
                                'inserted_id': str(tbill_result.inserted_id)
                            }
                        })
                        
                    except Exception as e:
                        session.abort_transaction()
                        logger.error(f'创建T账单事务失败: {str(e)}')
                        raise
        
        except Exception as e:
            logger.error(f'创建T账单失败: {str(e)}')
            raise
    
    def _update_tbill(self, data, openid):
        """更新T账单信息"""
        try:
            db = get_db()
            tbill_id = data.get('tbillId')
            
            if not tbill_id:
                return jsonify({
                    'success': False,
                    'message': '缺少tbillId参数'
                }), 400
            
            # 准备更新数据
            update_data = {
                'updateTime': datetime.utcnow()
            }
            
            # 允许更新的字段
            allowed_fields = ['date', 'remark']
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]
            
            # 执行更新
            result = db.tbills.update_one(
                {'_id': tbill_id, '_openid': openid},
                {'$set': update_data}
            )
            
            if result.modified_count == 0:
                return jsonify({
                    'success': False,
                    'message': 'T账单不存在或无权限更新'
                }), 404
            
            return jsonify({
                'success': True,
                'data': {
                    'modified_count': result.modified_count
                }
            })
        
        except Exception as e:
            logger.error(f'更新T账单失败: {str(e)}')
            raise
    
    def _get_tbill_detail(self, data, openid):
        """获取T账单详情"""
        try:
            db = get_db()
            tbill_id = data.get('tbillId')
            
            if not tbill_id:
                return jsonify({
                    'success': False,
                    'message': '缺少tbillId参数'
                }), 400
            
            # 查询T账单
            tbill = db.tbills.find_one({
                '_id': tbill_id,
                '_openid': openid
            })
            
            if not tbill:
                return jsonify({
                    'success': False,
                    'message': 'T账单不存在'
                }), 404
        
            
            return jsonify({
                'success': True,
                'data': tbill
            })
        
        except Exception as e:
            logger.error(f'获取T账单详情失败: {str(e)}')
            raise
    
    def _get_all_tbills(self, data, openid):
        """根据openId获取所有T账单 - 支持分页和筛选"""
        try:
            db = get_db()
            page = data.get('page', 1)
            page_size = data.get('pageSize', 20)
            stock_code = data.get('stockCode')
            
            skip = (page - 1) * page_size
            
            # 构建查询条件
            query: dict[str, Any] = {'_openid': openid}
            
            if stock_code and stock_code != 'all':
                query['stockCode'] = stock_code
            
            # 执行分页查询
            tbills = list(db.tbills.find(query)
                         .sort('date', -1)
                         .skip(skip)
                         .limit(page_size))
            
            # 获取总数
            total = db.tbills.count_documents(query)
            
            # 将ObjectId转换为字符串
            for tbill in tbills:
                tbill['_id'] = str(tbill['_id'])
                # 同时转换关联的交易记录ID
                if 'aTradeId' in tbill:
                    tbill['aTradeId'] = str(tbill['aTradeId'])
                if 'bTradeId' in tbill:
                    tbill['bTradeId'] = str(tbill['bTradeId'])
            
            return jsonify({
                'success': True,
                'data': tbills,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'total': total,
                    'hasMore': skip + len(tbills) < total
                }
            })
        
        except Exception as e:
            logger.error(f'获取T账单列表失败: {str(e)}')
            raise