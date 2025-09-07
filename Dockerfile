# ==============================
# 阶段1：构建依赖（仅用于安装依赖）
# ==============================
FROM python:3.13-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖（用于编译可能的C扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 升级pip和安装构建工具
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制依赖清单
COPY requirements.txt .

# 使用pip编译依赖并安装到指定目录（便于后续复制）
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# ==============================
# 阶段2：最终运行镜像（轻量化）
# ==============================
FROM python:3.13-slim

# 安装运行时必要的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 安全配置：创建非root用户运行服务（避免权限过高）
RUN groupadd -r botgroup --gid=1000 && \
    useradd -r -g botgroup --uid=1000 --home-dir=/app --shell=/bin/bash botuser

# 设置工作目录并设置正确的权限
WORKDIR /app
RUN chown -R botuser:botgroup /app

# 复制阶段1编译好的依赖
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# 升级pip并安装依赖（无需再次编译，速度更快）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels ~/.cache/pip

# 复制项目代码（复制所有必要文件）
COPY --chown=botuser:botgroup bot.py .
COPY --chown=botuser:botgroup config.py .
COPY --chown=botuser:botgroup handlers/ ./handlers/
COPY --chown=botuser:botgroup callback/ ./callback/
COPY --chown=botuser:botgroup utils/ ./utils/

# 配置环境变量（默认值，可通过docker run或compose覆盖）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    API_TIMEOUT=120 \
    ENVIRONMENT=production

# 切换到非root用户
USER botuser



# 暴露端口（如果需要健康检查端点）
# EXPOSE 8080

# 添加标签信息
LABEL maintainer="Bot Developer" \
      version="1.0" \
      description="Misaka Danmaku Telegram Bot"

# 启动命令（使用exec确保信号能正确传递给Python进程）
CMD ["python", "-u", "bot.py"]