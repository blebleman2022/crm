# 使用官方Python 3.11运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 升级pip并设置超时
RUN pip install --upgrade pip

# 复制requirements文件并安装Python依赖
COPY requirements-minimal.txt requirements.txt
COPY requirements-dev.txt .

# 安装生产环境依赖（增加超时和重试机制）
RUN pip install --no-cache-dir --timeout=1000 --retries=5 -r requirements.txt

# 如果是开发环境，安装开发依赖（通过构建参数控制）
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ] ; then pip install --no-cache-dir --timeout=1000 --retries=5 -r requirements-dev.txt ; fi

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p instance logs

# 设置权限
RUN chmod +x start_app.sh

# 创建非root用户
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/auth/login || exit 1

# 启动命令
CMD ["python", "run.py"]
