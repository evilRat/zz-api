#!/bin/bash

# 检查Python环境
echo "检查Python环境..."
python --version
pip --version

# 创建虚拟环境（可选）
# echo "创建虚拟环境..."
# python -m venv venv
# source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
echo "安装依赖包..."
pip install -r requirements.txt

# 启动服务
echo "启动 FastAPI 异步服务..."
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

uvicorn app:app --host 0.0.0.0 --port 5000 --reload