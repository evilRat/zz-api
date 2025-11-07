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
            mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/stock_trade_db')
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