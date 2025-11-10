import hashlib
import time
from typing import Optional


class BusinessIdGenerator:
    """业务ID生成器
    
    根据业务前缀、openId和时间戳生成唯一的业务ID
    """
    
    @staticmethod
    def generate_id(business_prefix: str, open_id: str, timestamp: Optional[float] = None) -> str:
        """生成唯一的业务ID
        
        Args:
            business_prefix: 业务前缀，如 'trade', 'tbill' 等
            open_id: 用户的openId
            timestamp: 时间戳，如果不提供则使用当前时间
            
        Returns:
            str: 生成的唯一业务ID
        """
        if timestamp is None:
            timestamp = time.time()
        
        # 创建一个基于业务前缀、openId和时间戳的字符串
        input_string = f"{business_prefix}:{open_id}:{timestamp}"
        
        # 使用MD5哈希算法生成固定长度的ID
        hash_object = hashlib.md5(input_string.encode('utf-8'))
        hex_dig = hash_object.hexdigest()
        
        # 返回生成的ID
        return hex_dig
    
    @staticmethod
    def generate_trade_id(open_id: str, timestamp: Optional[float] = None) -> str:
        """生成交易ID
        
        Args:
            open_id: 用户的openId
            timestamp: 时间戳，如果不提供则使用当前时间
            
        Returns:
            str: 生成的交易ID
        """
        return BusinessIdGenerator.generate_id("trade", open_id, timestamp)
    
    @staticmethod
    def generate_tbill_id(open_id: str, timestamp: Optional[float] = None) -> str:
        """生成T账单ID
        
        Args:
            open_id: 用户的openId
            timestamp: 时间戳，如果不提供则使用当前时间
            
        Returns:
            str: 生成的T账单ID
        """
        return BusinessIdGenerator.generate_id("tbill", open_id, timestamp)