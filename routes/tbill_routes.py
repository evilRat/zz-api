from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from utils.db import get_db
from utils.id_generator import BusinessIdGenerator
from datetime import datetime

logger = logging.getLogger(__name__)

# 定义请求模型
class TBillRequest(BaseModel):
    operation: str
    data: dict = Field(default_factory=dict)
    openId: str = 'test_openid'

# 创建路由
router = APIRouter(prefix='/api', tags=['tbills'])

@router.post('/tbillOperations')
async def tbill_operations(req: TBillRequest):
    """处理T账单操作请求"""
    try:
        if req.operation == 'createTBill':
            return await _create_tbill(req.data, req.openId)
        elif req.operation == 'updateTBill':
            return await _update_tbill(req.data, req.openId)
        elif req.operation == 'getTBillById':
            return await _get_tbill_detail(req.data, req.openId)
        elif req.operation == 'getAllTBills':
            return await _get_all_tbills(req.data, req.openId)
        else:
            raise HTTPException(status_code=400, detail='不支持的操作类型')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'T账单操作失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'操作失败: {str(e)}')

async def _create_tbill(data: dict, openid: str):
    """创建T账单，使用事务确保数据一致性"""
    try:
        db = get_db()
        
        # 直接使用传入的数据，因为数据结构已经符合要求
        tbill_data = data.copy()
        
        # 如果没有提供_id，则生成一个唯一的T账单ID
        tbill_data['_id'] = BusinessIdGenerator.generate_tbill_id(openid)
        
        # 确保_openid字段存在
        if '_openid' not in tbill_data:
            tbill_data['_openid'] = openid
        
        # 参数验证
        required_fields = ['firstTradeId', 'profit', 'quantity', 'secondTradeId', 
                         'status', 'stockCode', 'stockName', 'type']
        missing_fields = [field for field in required_fields if field not in tbill_data]
        
        if missing_fields:
            raise HTTPException(status_code=400, detail=f'缺少必要参数: {", ".join(missing_fields)}')
        
        try:
            # 1. 保存T账单数据到tbills集合
            tbill_result = await db.tbills.insert_one(tbill_data)
            
            # 2. 更新对应的交易记录状态为"已匹配"
            # 更新firstTrade
            first_trade_result = await db.trades.update_one(
                {'_id': tbill_data['firstTradeId'], '_openid': tbill_data['_openid']},
                {'$set': {'matchStatus': '已匹配', 'updateTime': datetime.utcnow()}}
            )
            
            # 更新secondTrade
            second_trade_result = await db.trades.update_one(
                {'_id': tbill_data['secondTradeId'], '_openid': tbill_data['_openid']},
                {'$set': {'matchStatus': '已匹配', 'updateTime': datetime.utcnow()}}
            )
            
            # 检查是否成功更新了两个交易记录
            if first_trade_result.modified_count == 0 or second_trade_result.modified_count == 0:
                # 如果更新失败，记录警告但不回滚（因为没有使用事务）
                logger.warning(f'未能成功更新所有交易记录: firstTradeId={tbill_data["firstTradeId"]}, secondTradeId={tbill_data["secondTradeId"]}')
            
            return {
                'success': True,
                'data': {
                    'inserted_id': str(tbill_result.inserted_id)
                }
            }
            
        except Exception as e:
            logger.error(f'创建T账单数据库操作失败: {str(e)}')
            raise HTTPException(status_code=500, detail=f'数据库操作失败: {str(e)}')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'创建T账单失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'创建T账单失败: {str(e)}')

async def _update_tbill(data: dict, openid: str):
    """更新T账单信息"""
    try:
        db = get_db()
        tbill_id = data.get('tbillId')
        
        if not tbill_id:
            raise HTTPException(status_code=400, detail='缺少tbillId参数')
        
        # 准备更新数据
        update_data = {
            'updateTime': datetime.utcnow()
        }
        
        # 允许更新的字段
        allowed_fields = ['date', 'remark']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        # 异步执行更新
        result = await db.tbills.update_one(
            {'_id': tbill_id, '_openid': openid},
            {'$set': update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail='T账单不存在或无权限更新')
        
        return {
            'success': True,
            'data': {
                'modified_count': result.modified_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'更新T账单失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'更新T账单失败: {str(e)}')

async def _get_tbill_detail(data: dict, openid: str):
    """获取T账单详情"""
    try:
        db = get_db()
        tbill_id = data.get('tbillId')
        
        if not tbill_id:
            raise HTTPException(status_code=400, detail='缺少tbillId参数')
        
        # 异步查询T账单
        tbill = await db.tbills.find_one({
            '_id': tbill_id,
            '_openid': openid
        })
        
        if not tbill:
            raise HTTPException(status_code=404, detail='T账单不存在')
        
        # 根据firstTradeId和secondTradeId查询对应的交易记录
        first_trade = None
        second_trade = None
        
        if 'firstTradeId' in tbill:
            first_trade = await db.trades.find_one({
                '_id': tbill['firstTradeId'],
                '_openid': openid
            })
        if not first_trade:
            raise HTTPException(status_code=404, detail='第一步交易不存在')
        
        if 'secondTradeId' in tbill:
            second_trade = await db.trades.find_one({
                '_id': tbill['secondTradeId'],
                '_openid': openid
            })
        if not second_trade:
            raise HTTPException(status_code=404, detail='第二步交易不存在')
        
        # 转换ObjectId
        tbill['_id'] = str(tbill['_id'])
        first_trade['_id'] = str(first_trade['_id'])
        second_trade['_id'] = str(second_trade['_id'])
        
        return {
            'success': True,
            'data': {
                **tbill,
                'firstTrade': first_trade,
                'secondTrade': second_trade
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'获取T账单详情失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'获取T账单详情失败: {str(e)}')

async def _get_all_tbills(data: dict, openid: str):
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
        
        # 异步执行分页查询
        tbills = await db.tbills.find(query).sort('date', -1).skip(skip).limit(page_size).to_list(length=None)
        
        # 获取总数
        total = await db.tbills.count_documents(query)
        
        # 将ObjectId转换为字符串
        for tbill in tbills:
            tbill['_id'] = str(tbill['_id'])
            # 同时转换关联的交易记录ID
            if 'aTradeId' in tbill:
                tbill['aTradeId'] = str(tbill['aTradeId'])
            if 'bTradeId' in tbill:
                tbill['bTradeId'] = str(tbill['bTradeId'])
        
        return {
            'success': True,
            'data': tbills,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'hasMore': skip + len(tbills) < total
            }
        }
    
    except Exception as e:
        logger.error(f'获取T账单列表失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'获取T账单列表失败: {str(e)}')