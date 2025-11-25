import httpx
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class WeChatAPI:
    """微信API工具类"""
    
    # 微信API基础URL
    BASE_URL = "https://api.weixin.qq.com/sns/jscode2session"
    
    @staticmethod
    async def get_open_id(code: str) -> Optional[Dict[str, Any]]:
        """通过微信登录code获取用户openId (异步)
        
        Args:
            code: 微信登录时获取的code
            
        Returns:
            dict: 包含openId等信息的字典，失败时返回None
        """
        try:
            # 从环境变量获取微信小程序配置
            app_id = os.environ.get('WX_APP_ID')
            app_secret = os.environ.get('WX_APP_SECRET')
            
            if not app_id or not app_secret:
                logger.error("微信小程序配置缺失: 请在.env文件中设置WX_APP_ID和WX_APP_SECRET")
                return None
            
            # 构建请求参数
            params = {
                'appid': app_id,
                'secret': app_secret,
                'js_code': code,
                'grant_type': 'authorization_code'
            }
            
            # 使用异步HTTP客户端发送请求到微信API
            async with httpx.AsyncClient() as client:
                response = await client.get(WeChatAPI.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                
                # 解析响应
                data = response.json()
                
                # 检查是否有错误
                if 'errcode' in data and data['errcode'] != 0:
                    logger.error(f"微信API错误: errcode={data['errcode']}, errmsg={data['errmsg']}")
                    return None
                
                # 返回成功结果
                return {
                    'open_id': data.get('openid'),
                    'session_key': data.get('session_key'),
                    'union_id': data.get('unionid')
                }
            
        except httpx.RequestError as e:
            logger.error(f"请求微信API失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取openId时发生未知错误: {str(e)}")
            return None