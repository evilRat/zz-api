from pymongo import MongoClient
import os
import logging

logger = logging.getLogger(__name__)

# 全局数据库连接
client = None
db = None

def get_db():
    """获取数据库连接"""
    global client, db
    
    if db is None:
        try:
            # 获取MongoDB连接参数
            mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/stock_trade_db')
            mongo_username = os.environ.get('MONGO_USERNAME')
            mongo_password = os.environ.get('MONGO_PASSWORD')
            
            # 如果提供了用户名和密码，则使用认证方式连接
            if mongo_username and mongo_password:
                # 解析URI并添加认证信息
                from urllib.parse import urlparse, urlunparse
                parsed_uri = urlparse(mongo_uri)
                
                # 构建带认证信息的URI
                netloc = f"{mongo_username}:{mongo_password}@{parsed_uri.hostname}"
                if parsed_uri.port:
                    netloc += f":{parsed_uri.port}"
                
                authenticated_uri = urlunparse((
                    parsed_uri.scheme,
                    netloc,
                    parsed_uri.path,
                    parsed_uri.params,
                    parsed_uri.query,
                    parsed_uri.fragment
                ))
                
                client = MongoClient(authenticated_uri)
            else:
                # 使用原始URI连接（无认证）
                client = MongoClient(mongo_uri)
            
            db = client.get_default_database()
            # 测试连接
            db.command('ping')
            logger.info('MongoDB连接成功')
        except Exception as e:
            logger.error(f'MongoDB连接失败: {str(e)}')
            raise
    
    return db

def close_db():
    """关闭数据库连接"""
    global client
    if client:
        client.close()
        logger.info('MongoDB连接已关闭')