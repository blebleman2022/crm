# 使用官方Python 3.11运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production

# 配置国内镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian-security/ bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置pip使用国内镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --upgrade pip

# 复制requirements文件并安装Python依赖
COPY requirements.txt .
COPY requirements-dev.txt .

# 安装生产环境依赖（使用国内镜像源）
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r requirements.txt

# 如果是开发环境，安装开发依赖（通过构建参数控制）
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ] ; then \
    pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r requirements-dev.txt ; fi

# 复制启动脚本和配置文件
COPY start.sh .
COPY init-database.sh .
COPY gunicorn.conf.py .

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p instance logs

# 确保数据库文件存在并设置权限
RUN if [ -f "instance/edu_crm.db" ]; then \
        echo "✅ 找到数据库文件: instance/edu_crm.db"; \
        ls -la instance/edu_crm.db; \
    else \
        echo "❌ 数据库文件不存在，将在运行时创建"; \
        touch instance/edu_crm.db; \
    fi && \
    chmod 755 instance logs && \
    chmod 666 instance/edu_crm.db

# 设置权限
RUN chmod +x start.sh init-database.sh

# 创建非root用户
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/instance /app/logs

# 暴露端口
EXPOSE 80

# 健康检查 - 增加启动时间，因为Flask应用需要时间初始化
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:80/health || curl -f http://localhost:80/auth/login || exit 1

# 切换到非root用户
USER appuser

# 启动命令 - 使用初始化脚本
CMD ["./init-database.sh", "./start.sh"]
