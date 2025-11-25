from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入数据库和路由
from utils.db import init_db, close_db, get_db
from utils.wechat_utils import WeChatAPI
from routes.trade_routes import router as trade_router
from routes.tbill_routes import router as tbill_router
from routes.stock_routes import router as stock_router

# 定义应用生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化数据库
    logger.info('应用启动，初始化数据库...')
    await init_db()
    yield
    # 关闭：关闭数据库连接
    logger.info('应用关闭，关闭数据库连接...')
    await close_db()

# 创建FastAPI应用
app = FastAPI(
    title='Stock Trading API',
    description='Stock Trading & T-Bill Management REST API',
    version='2.0.0',
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 注册路由
app.include_router(trade_router)
app.include_router(tbill_router)
app.include_router(stock_router)

# 定义请求模型
class OpenIdRequest(BaseModel):
    code: str

# 健康检查接口
@app.get('/health')
async def health_check():
    """健康检查接口"""
    return {
        'status': 'ok',
        'message': 'API服务运行正常'
    }

# 微信登录获取openId接口
@app.post('/api/getOpenId')
async def get_open_id(req: OpenIdRequest):
    """通过微信登录code获取用户openId"""
    try:
        if not req.code:
            raise HTTPException(status_code=400, detail='缺少code参数')
        
        # 调用异步微信API获取openId
        result = await WeChatAPI.get_open_id(req.code)
        if not result or not result.get('open_id'):
            raise HTTPException(status_code=500, detail='获取openId失败')
        
        # 返回openId给前端
        return {
            'success': True,
            'data': {
                'openId': result['open_id'],
                'unionId': result.get('union_id')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'获取openId接口异常: {str(e)}')
        raise HTTPException(status_code=500, detail=f'服务器内部错误: {str(e)}')

# 自定义异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """统一处理HTTP异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'success': False,
            'message': exc.detail,
            'error': str(exc.detail)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """统一处理未捕获异常"""
    logger.error(f'未捕获异常: {str(exc)}')
    return JSONResponse(
        status_code=500,
        content={
            'success': False,
            'message': '服务器内部错误',
            'error': str(exc)
        }
    )

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG') == 'True'
    uvicorn.run('app:app', host='0.0.0.0', port=port, reload=debug)