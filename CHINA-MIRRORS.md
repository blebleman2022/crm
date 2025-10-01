# 国内镜像源配置指南

## 📋 概述

为了解决在中国大陆地区访问国外镜像源速度慢的问题，本项目已全面配置国内镜像源，包括：

- **APT镜像源**: 阿里云
- **pip镜像源**: 清华大学
- **Docker镜像源**: 中科大、网易、百度云
- **Git镜像源**: cnpmjs、fastgit
- **Docker Hub镜像**: 阿里云容器镜像服务

## 🚀 快速配置

### 方法1：使用一键配置脚本（推荐）

```bash
# 执行国内镜像源配置脚本
./setup-china-mirrors.sh
```

### 方法2：使用更新脚本（自动配置）

```bash
# 执行项目更新脚本（已集成镜像源配置）
./update-server.sh
```

## 🔧 手动配置

### 1. APT镜像源配置

```bash
# 备份原始源列表
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

# Debian系统
sudo tee /etc/apt/sources.list > /dev/null <<EOF
deb https://mirrors.aliyun.com/debian/ bullseye main contrib non-free
deb https://mirrors.aliyun.com/debian-security/ bullseye-security main
deb https://mirrors.aliyun.com/debian/ bullseye-updates main contrib non-free
EOF

# Ubuntu系统
sudo tee /etc/apt/sources.list > /dev/null <<EOF
deb https://mirrors.aliyun.com/ubuntu/ focal main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-security main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ focal-updates main restricted universe multiverse
EOF

# 更新包列表
sudo apt update
```

### 2. pip镜像源配置

```bash
# 创建pip配置目录
mkdir -p ~/.pip

# 配置pip镜像源
cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF
```

### 3. Docker镜像源配置

```bash
# 创建Docker配置目录
sudo mkdir -p /etc/docker

# 配置Docker镜像源
sudo tee /etc/docker/daemon.json > /dev/null << EOF
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn",
        "https://hub-mirror.c.163.com",
        "https://mirror.baidubce.com"
    ]
}
EOF

# 重启Docker服务
sudo systemctl restart docker
```

### 4. Git镜像源配置

```bash
# 配置GitHub镜像
git config --global url."https://github.com.cnpmjs.org/".insteadOf "https://github.com/"
```

## 📦 Docker镜像优化

### Dockerfile优化

项目的Dockerfile已优化为使用国内镜像：

```dockerfile
# 使用官方Python镜像（通过Docker镜像源加速）
FROM python:3.11-slim

# 配置Debian镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 配置pip镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### Docker Compose优化

构建时使用国内镜像：

```bash
# 使用国内镜像构建
docker-compose build --no-cache

# 或者设置环境变量
export DOCKER_BUILDKIT=1
docker-compose build
```

## 🛠️ 安装工具（国内镜像）

### Docker安装

```bash
# 使用阿里云Docker安装脚本
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
```

### Docker Compose安装

```bash
# 使用DaoCloud镜像下载
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
sudo curl -L "https://get.daocloud.io/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 📊 镜像源速度对比

| 镜像源类型 | 国外源 | 国内源 | 速度提升 |
|------------|--------|--------|----------|
| **APT** | deb.debian.org | mirrors.aliyun.com | 5-10倍 |
| **pip** | pypi.org | pypi.tuna.tsinghua.edu.cn | 3-8倍 |
| **Docker** | docker.io | docker.mirrors.ustc.edu.cn | 10-20倍 |
| **Git** | github.com | github.com.cnpmjs.org | 2-5倍 |

## 🔍 验证配置

### 验证APT镜像源

```bash
apt policy
```

### 验证pip镜像源

```bash
pip config list
```

### 验证Docker镜像源

```bash
docker info | grep -A 10 "Registry Mirrors"
```

### 验证Git镜像源

```bash
git config --global --list | grep url
```

## 🚨 注意事项

1. **系统兼容性**: 配置脚本支持Debian和Ubuntu系统
2. **权限要求**: 某些配置需要sudo权限
3. **网络环境**: 在某些网络环境下可能需要调整镜像源
4. **版本更新**: 镜像源地址可能会变化，请定期更新

## 📞 故障排除

### 常见问题

1. **GPG密钥错误**
   ```bash
   sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys [KEY_ID]
   ```

2. **Docker镜像拉取失败**
   ```bash
   # 重启Docker服务
   sudo systemctl restart docker
   ```

3. **pip安装超时**
   ```bash
   # 增加超时时间
   pip install --timeout 300 -r requirements.txt
   ```

### 恢复原始配置

```bash
# 恢复APT源
sudo cp /etc/apt/sources.list.backup /etc/apt/sources.list

# 删除pip配置
rm ~/.pip/pip.conf

# 恢复Docker配置
sudo rm /etc/docker/daemon.json
sudo systemctl restart docker
```

## 📈 性能优化建议

1. **选择最近的镜像源**: 根据地理位置选择最近的镜像源
2. **定期更新**: 定期更新镜像源列表
3. **监控速度**: 使用工具监控下载速度
4. **备用方案**: 准备多个镜像源作为备用

通过配置国内镜像源，可以显著提升在中国大陆地区的部署和开发效率！
