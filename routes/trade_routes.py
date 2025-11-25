from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import logging
from utils.db import get_db
from utils.id_generator import BusinessIdGenerator
from datetime import datetime

logger = logging.getLogger(__name__)

# 定义请求/响应模型
class TradeRequest(BaseModel):
    operation: str
    data: dict = Field(default_factory=dict)
    openId: str = 'test_openid'

class TradeResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = None
    pagination: Any = None

# 创建路由
router = APIRouter(prefix='/api', tags=['trades'])

@router.post('/tradeOperations')
async def trade_operations(req: TradeRequest):
    """处理交易操作请求"""
    try:
        if req.operation == 'getAllTrades':
            return await _get_all_trades(req.data, req.openId)
        elif req.operation == 'addTrade':
            return await _add_trade(req.data, req.openId)
        elif req.operation == 'deleteTrade':
            return await _delete_trade(req.data, req.openId)
        elif req.operation == 'getTradeById':
            return await _get_trade_by_id(req.data, req.openId)
        else:
            raise HTTPException(status_code=400, detail='不支持的操作类型')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'交易操作失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'操作失败: {str(e)}')

async def _get_all_trades(data: dict, openid: str):
    """获取所有交易记录 - 支持分页和筛选"""
    try:
        db = get_db()
        page = data.get('page', 1)
        page_size = data.get('pageSize', 20)
        match_status = data.get('matchStatus')
        stock_code = data.get('stockCode')
        trade_type = data.get('type')
        
        skip = (page - 1) * page_size
        
        # 构建查询条件
        query: dict[str, Any] = {'_openid': openid}
        
        if match_status and match_status != 'all':
            query['matchStatus'] = match_status
        
        if stock_code and stock_code != 'all':
            query['stockCode'] = stock_code
        
        if trade_type and trade_type != 'all':
            query['type'] = trade_type
        
        # 异步执行分页查询
        trades = await db.trades.find(query).sort('createTime', -1).skip(skip).limit(page_size).to_list(length=None)
        
        # 获取总数
        total = await db.trades.count_documents(query)
        
        # 将ObjectId转换为字符串
        for trade in trades:
            trade['_id'] = str(trade['_id'])
        
        return {
            'success': True,
            'data': trades,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'hasMore': skip + len(trades) < total
            }
        }
    
    except Exception as e:
        logger.error(f'获取交易记录失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'获取交易记录失败: {str(e)}')

async def _add_trade(data: dict, openid: str):
    """添加新交易记录"""
    try:
        db = get_db()
        
        # 验证必要字段
        required_fields = ['date', 'stockCode', 'stockName', 'type', 'price', 'quantity']
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f'缺少必要字段: {field}')
        
        # 生成唯一的交易ID
        trade_id = BusinessIdGenerator.generate_trade_id(openid)
        
        # 准备插入数据
        trade_data = {
            '_id': trade_id,
            **data,
            '_openid': openid,
            'matchStatus': 'unmatched',  # 默认状态为未匹配
            'createTime': datetime.utcnow(),
            'updateTime': datetime.utcnow()
        }
        
        # 异步插入数据
        result = await db.trades.insert_one(trade_data)
        
        return {
            'success': True,
            'data': {
                'inserted_id': str(result.inserted_id)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'添加交易记录失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'添加交易记录失败: {str(e)}')

async def _delete_trade(data: dict, openid: str):
    """删除交易记录"""
    try:
        db = get_db()
        trade_id = data.get('tradeId')
        
        if not trade_id:
            raise HTTPException(status_code=400, detail='缺少tradeId参数')
        
        # 异步执行删除
        result = await db.trades.delete_one({
            '_id': trade_id,
            '_openid': openid
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail='交易记录不存在或无权限删除')
        
        return {
            'success': True,
            'data': {
                'deleted_count': result.deleted_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'删除交易记录失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'删除交易记录失败: {str(e)}')

async def _get_trade_by_id(data: dict, openid: str):
    """根据ID获取交易记录"""
    try:
        db = get_db()
        trade_id = data.get('tradeId')
        
        if not trade_id:
            raise HTTPException(status_code=400, detail='缺少tradeId参数')
        
        # 异步查询记录
        trade = await db.trades.find_one({
            '_id': trade_id,
            '_openid': openid
        })
        
        if not trade:
            raise HTTPException(status_code=404, detail='交易记录不存在')
        
        # 转换ObjectId为字符串
        trade['_id'] = str(trade['_id'])
        
        return {
            'success': True,
            'data': trade
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'获取交易记录失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f'获取交易记录失败: {str(e)}')