# Gunicorn配置文件
import os

# 服务器套接字
bind = "0.0.0.0:80"
backlog = 2048

# 工作进程
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# 重启
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "crm-app"

# 安全
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 应用模块
wsgi_module = "run:app"
pythonpath = "/app"

# 用户和组 (Docker中已经切换用户，这里不需要再设置)
# user = "appuser"
# group = "appuser"

# 临时目录
tmp_upload_dir = None

# SSL (如果需要)
# keyfile = None
# certfile = None
