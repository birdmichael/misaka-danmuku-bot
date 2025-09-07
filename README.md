# Misaka Danmaku Bot

Telegram 机器人指令与 Misaka Danmaku API 的对接

## 快速部署

### 使用 Docker Compose（推荐）

1. 创建 `docker-compose.yml` 文件：

```yaml
version: "3.8"

services:
  # Telegram弹幕机器人服务
  misaka-danmaku-bot:
    image: ghcr.io/balge/misaka-danmuku-bot:latest
    container_name: misaka-danmaku-bot
    restart: unless-stopped
    network_mode: host

    # 环境变量配置
    environment:
      # Telegram机器人必填配置
      - TELEGRAM_BOT_TOKEN=机器人token，botfather获取
      - ALLOWED_USER_IDS=用户id，多个用逗号分隔，get My Id 获取
      - ADMIN_USER_IDS=管理员用户id，多个用逗号分隔，拥有完整功能权限

      # Misaka Danmaku API必填配置
      - DANMAKU_API_BASE_URL=http://127.0.0.1:7768/api/control
      - DANMAKU_API_KEY=外部apikey

      # 代理配置（可选）
      - HTTP_PROXY=http://127.0.0.1:2083
      - HTTPS_PROXY=http://127.0.0.1:2083
      - NO_PROXY=localhost,127.0.0.1

      # TMDB配置（可选，用于智能搜索辅助）
      - TMDB_API_KEY=your_tmdb_api_key_here

      # TVDB配置（可选，用于TVDB链接解析）
      - TVDB_API_KEY=your_tvdb_api_key_here

      # BGM配置（可选，用于Bangumi链接解析）
      - BGM_ACCESS_TOKEN=your_bgm_access_token_here

      # 其他可选配置
      - API_TIMEOUT=120
      - LOG_LEVEL=INFO
```

2. 启动服务：

```bash
docker-compose up -d
```

### 环境变量说明

#### 必填配置

- `TELEGRAM_BOT_TOKEN`: Telegram 机器人 Token
- `ALLOWED_USER_IDS`: 允许使用机器人的用户 ID（多个用户用逗号分隔）
- `ADMIN_USER_IDS`: 管理员用户 ID（多个用户用逗号分隔，拥有完整功能权限）
- `DANMAKU_API_BASE_URL`: Misaka Danmaku API 基础地址
- `DANMAKU_API_KEY`: Misaka Danmaku API 密钥

#### 可选配置

- `HTTP_PROXY`: HTTP 代理地址
- `HTTPS_PROXY`: HTTPS 代理地址
- `NO_PROXY`: 不使用代理的地址列表
- `API_TIMEOUT`: API 请求超时时间（秒，默认 120，可根据网络情况调整）
- `LOG_LEVEL`: 日志级别（INFO/DEBUG/WARNING/ERROR，默认 INFO）
- `TMDB_API_KEY`: TMDB API 密钥（用于智能搜索辅助，从 https://www.themoviedb.org/settings/api 获取）
- `TVDB_API_KEY`: TVDB API 密钥（用于TVDB链接解析和媒体信息获取，从 https://thetvdb.com/api-information 获取）
- `BGM_ACCESS_TOKEN`: Bangumi API 访问令牌（用于BGM链接解析和媒体信息获取，从 https://bgm.tv/dev/app 创建应用获取）

### 本地开发

1. 克隆项目：

```bash
git clone https://github.com/balge/misaka-danmuku-bot.git
cd misaka-danmuku-bot
```

2. 复制配置文件：

```bash
cp .env.example .env
```

3. 编辑 `.env` 文件，填入必要的配置

4. 安装依赖并运行：

```bash
pip install -r requirements.txt
python bot.py
```

## 权限说明

### 管理员权限
管理员用户（在 `ADMIN_USER_IDS` 中配置）拥有完整的功能权限：
- ✅ 媒体搜索和导入 (`/search`)
- ✅ 自动导入功能 (`/auto`)
- ✅ URL链接导入 (`/url`)
- ✅ 刷新数据源 (`/refresh`)
- ✅ Token管理 (`/tokens`)
- ✅ 用户管理 (`/addUser`, `/deleteUser`, `/listUser`)
- ✅ 帮助和取消操作 (`/help`, `/cancel`)
- ✅ 查询全局配额 (`/quota`，需控制 Token)
- ✅ 查询任务状态 (`/tasks [状态码]`)


### 普通用户权限
普通用户（在 `ALLOWED_USER_IDS` 中配置但不在 `ADMIN_USER_IDS` 中）仅有基础功能权限：
- ✅ 媒体搜索和导入 (`/search`)
- ✅ 自动导入功能 (`/auto`)
- ✅ 帮助和取消操作 (`/help`, `/cancel`)
- ✅ 查询全局配额 (`/quota`)
- ✅ 查询任务状态 (`/tasks [状态码]`)
- ❌ URL链接导入 (`/url`) - 需要管理员权限
- ❌ 刷新数据源 (`/refresh`) - 需要管理员权限
- ❌ Token管理 (`/tokens`) - 需要管理员权限
- ❌ 用户管理 (`/addUser`, `/deleteUser`, `/listUser`) - 需要管理员权限


> 💡 **提示**: 普通用户可以看到所有功能选项，但点击管理员专用功能时会收到权限不足的提示。

## 功能特性

- 🤖 Telegram 机器人集成
- 🔐 用户权限管理（管理员/普通用户分级）
- 📇 动态用户管理命令 (`/addUser`, `/deleteUser`, `/listUser`)
- 🎯 媒体搜索和导入
- 🔄 自动导入功能
- 🧠 TMDB智能搜索辅助（自动识别电影/电视剧类型）
- 📺 TVDB链接解析支持（自动识别TVDB链接并获取媒体信息）
- 🎭 豆瓣链接解析支持（自动识别豆瓣链接并获取媒体信息）
- 🌟 IMDB链接解析支持（自动识别IMDB链接并获取媒体信息）
- 🎯 Bangumi(BGM)链接解析支持（自动识别BGM链接并获取媒体信息，支持API和爬虫双模式）
- 📋 任务状态查询（`/tasks`，支持按状态码过滤：0=all,1=in_progress,2=completed）
- 🌐 代理支持
- 📊 详细日志记录
- 🔥 热重载开发支持
- 🔢 全局配额查询

## 许可证

MIT License
