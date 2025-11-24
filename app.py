from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from dotenv import load_dotenv
import os
import logging
import json

# 加载环境变量
load_dotenv()

# 初始化Flask应用
app = Flask(__name__)
app.config.from_object(__name__)

# 配置JSON序列化
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_MIMETYPE'] = 'application/json'
app.config['JSON_AS_ASCII'] = False

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化API
api = Api(app)

# 导入路由模块
from routes.trade_routes import TradeOperations
from routes.tbill_routes import TBillOperations
from routes.stock_routes import StockCodeLookupResource
# 导入微信工具
from utils.wechat_utils import WeChatAPI

# 注册路由
api.add_resource(TradeOperations, '/api/tradeOperations')
api.add_resource(TBillOperations, '/api/tbillOperations')
api.add_resource(StockCodeLookupResource, '/api/stockCodeLookup')

# 微信登录获取openId接口
@app.route('/api/getOpenId', methods=['POST'])
def get_open_id():
    """通过微信登录code获取用户openId"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '请求数据不能为空'
            }), 400
        
        # 获取微信登录code
        code = data.get('code')
        if not code:
            return jsonify({
                'success': False,
                'message': '缺少code参数'
            }), 400
        
        # 调用微信API获取openId
        result = WeChatAPI.get_open_id(code)
        if not result or not result.get('open_id'):
            return jsonify({
                'success': False,
                'message': '获取openId失败'
            }), 500
        
        # 返回openId给前端
        return jsonify({
            'success': True,
            'data': {
                'openId': result['open_id'],
                'unionId': result.get('union_id')
            }
        })
        
    except Exception as e:
        logger.error(f'获取openId接口异常: {str(e)}')
        return jsonify({
            'success': False,
            'message': '服务器内部错误',
            'error': str(e)
        }), 500

# 健康检查接口
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'API服务运行正常'
    })

# CORS中间件
@app.after_request
def after_request(response):
    response.headers.set('Access-Control-Allow-Origin', '*')
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.set('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# 统一错误处理
@app.errorhandler(404)
def not_found(error):
    return {
        'success': False,
        'message': '接口不存在'
    }, 404

@app.errorhandler(500)
def internal_error(error):
    error_msg = str(error)
    logger.error(f'内部错误: {error_msg}')
    return {
        'success': False,
        'message': '服务器内部错误',
        'error': error_msg
    }, 500

# 处理JSON序列化错误
@app.errorhandler(TypeError)
def handle_type_error(error):
    error_msg = str(error)
    logger.error(f'类型错误: {error_msg}')
    return {
        'success': False,
        'message': '数据序列化错误',
        'error': error_msg
    }, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG') == 'True')