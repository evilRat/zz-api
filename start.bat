@echo off

rem 检查Python环境
echo 检查Python环境...
python --version
pip --version

rem 创建虚拟环境（可选）
rem echo 创建虚拟环境...
rem python -m venv venv
rem venv\Scripts\activate

rem 安装依赖
echo 安装依赖包...
pip install -r requirements.txt

rem 启动服务
echo 启动 FastAPI 异步服务...
if exist ".env" (
    for /f "tokens=*" %%a in ('findstr /v "^#" .env') do set "%%a"
)

uvicorn app:app --host 0.0.0.0 --port 5000 --reload