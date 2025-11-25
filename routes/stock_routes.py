from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from utils.stock_utils import StockCodeLookup as StockLookupUtil

logger = logging.getLogger(__name__)

# 定义请求模型
class StockCodeRequest(BaseModel):
    stockCode: str

# 创建路由
router = APIRouter(prefix='/api', tags=['stocks'])

@router.post('/stockCodeLookup')
async def stock_code_lookup_post(req: StockCodeRequest):
    """处理股票代码查询请求 (POST)"""
    try:
        if not req.stockCode:
            raise HTTPException(status_code=400, detail='缺少stockCode参数')
        
        # 调用股票查询工具
        result = StockLookupUtil.get_stock_info(req.stockCode)
        
        if result['success']:
            return result
        else:
            # 根据错误信息返回不同的状态码
            if '不支持的股票代码格式' in result.get('message', ''):
                raise HTTPException(status_code=400, detail=result['message'])
            elif '无法获取股票信息' in result.get('message', ''):
                raise HTTPException(status_code=404, detail=result['message'])
            else:
                raise HTTPException(status_code=500, detail=result['message'])
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f'股票代码查询失败: {error_msg}')
        raise HTTPException(status_code=500, detail=f'查询失败: {error_msg}')

@router.get('/stockCodeLookup')
async def stock_code_lookup_get(stockCode: str):
    """支持GET请求，方便测试"""
    try:
        if not stockCode:
            raise HTTPException(status_code=400, detail='缺少stockCode参数')
        
        # 调用股票查询工具
        result = StockLookupUtil.get_stock_info(stockCode)
        
        if result['success']:
            return result
        else:
            if '不支持的股票代码格式' in result.get('message', ''):
                raise HTTPException(status_code=400, detail=result['message'])
            elif '无法获取股票信息' in result.get('message', ''):
                raise HTTPException(status_code=404, detail=result['message'])
            else:
                raise HTTPException(status_code=500, detail=result['message'])
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f'股票代码查询失败: {error_msg}')
        raise HTTPException(status_code=500, detail=f'查询失败: {error_msg}')