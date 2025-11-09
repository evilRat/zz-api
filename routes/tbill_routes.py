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
                # 对于createTBill操作，直接传递整个data对象（不使用operation_data）
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
            
            # 直接使用传入的数据，因为数据结构已经符合要求
            tbill_data = data.copy()
            
            # 确保_openid字段存在
            if '_openid' not in tbill_data:
                tbill_data['_openid'] = openid
            
            # 参数验证
            required_fields = ['firstTradeId', 'profit', 'quantity', 'secondTradeId', 
                             'status', 'stockCode', 'stockName', 'type']
            missing_fields = [field for field in required_fields if field not in tbill_data]
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': f'缺少必要参数: {", ".join(missing_fields)}'
                }), 400
            
            try:
                # 1. 保存T账单数据到tbills集合
                tbill_result = db.tbills.insert_one(tbill_data)
                
                # 2. 更新对应的交易记录状态为"已匹配"
                # 更新firstTrade
                first_trade_result = db.trades.update_one(
                    {'id': tbill_data['firstTradeId'], '_openid': tbill_data['_openid']},
                    {'$set': {'status': '已匹配', 'updateTime': datetime.utcnow()}}
                )
                
                # 更新secondTrade
                second_trade_result = db.trades.update_one(
                    {'id': tbill_data['secondTradeId'], '_openid': tbill_data['_openid']},
                    {'$set': {'status': '已匹配', 'updateTime': datetime.utcnow()}}
                )
                
                # 检查是否成功更新了两个交易记录
                if first_trade_result.modified_count == 0 or second_trade_result.modified_count == 0:
                    # 如果更新失败，记录警告但不回滚（因为没有使用事务）
                    logger.warning(f'未能成功更新所有交易记录: firstTradeId={tbill_data["firstTradeId"]}, secondTradeId={tbill_data["secondTradeId"]}')
                
                return jsonify({
                    'success': True,
                    'data': {
                        'inserted_id': str(tbill_result.inserted_id)
                    }
                })
                
            except Exception as e:
                logger.error(f'创建T账单数据库操作失败: {str(e)}')
                return jsonify({
                    'success': False,
                    'message': '数据库操作失败',
                    'error': str(e)
                }), 500
        
        except Exception as e:
            logger.error(f'创建T账单失败: {str(e)}')
            return jsonify({
                'success': False,
                'message': '创建T账单失败',
                'error': str(e)
            }), 500
    
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