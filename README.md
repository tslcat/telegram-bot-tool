# Telegram 个人工具箱（记事本、图床、收藏夹） Bot

一个功能强大的 Telegram Bot，支持图床、记事本、网络收藏夹，并支持 WebDAV 自动备份和导入导出。完全 Docker 化，支持 GitHub Actions 自动构建并推送到 Docker Hub。

## ✨ 功能特性

1. **📷 图床功能**  
   - 直接在 Telegram 发送图片给 Bot，自动保存并返回可通过域名访问的公开链接  
   - 支持自定义域名（需反向代理配置）  
   - 图片保存在本地 `data/images/` 目录

2. **📝 记事本功能**  
   - 添加、修改、删除、查看记事本  
   - 支持标题和内容  
   - 通过内联键盘方便管理

3. **🔖 网络收藏夹**  
   - 添加、修改、删除收藏夹  
   - 支持 URL + 备注说明  
   - 方便分类管理

4. **☁️ 数据备份与恢复**  
   - 支持 WebDAV 自动/手动备份（数据库 + 图片打包）  
   - 支持导入导出（上传 zip 文件恢复）  
   - 可设置定时自动备份

## 🚀 快速部署（推荐 Docker）

### 1. 获取代码

```bash
git clone https://github.com/你的用户名/telegram-bot-tool.git
cd telegram-bot-tool
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
# Telegram Bot Token (从 @BotFather 获取)
TELEGRAM_TOKEN=你的bot_token

# 你的 Telegram Chat ID (发送 /start 给 @userinfobot 获取)
OWNER_CHAT_ID=你的chat_id

# 公开访问域名（必须配置，否则图床链接无效）
PUBLIC_BASE_URL=https://yourdomain.com

# Web 服务器端口（Docker 内部）
WEB_PORT=8080

# WebDAV 配置（用于备份，可选）
WEBDAV_URL=https://your-webdav-server.com/remote.php/dav/files/username/
WEBDAV_USERNAME=你的webdav用户名
WEBDAV_PASSWORD=你的webdav密码

# 自动备份间隔（小时，0 表示关闭）
BACKUP_INTERVAL_HOURS=24
```

### 3. 使用 Docker 运行

```bash
docker-compose up -d
```

首次运行会自动创建 `data/` 目录和数据库。

访问 `http://你的服务器IP:8080/images/` 可查看图片（需配置域名反向代理到 8080 端口）。

### 4. 配置域名反向代理（推荐 Nginx + Cloudflare / Let's Encrypt）

示例 Nginx 配置：

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location /images/ {
        proxy_pass http://localhost:8080/images/;
        proxy_set_header Host $host;
    }

    # 可选：添加其他路由保护
}
```

确保 `PUBLIC_BASE_URL=https://yourdomain.com`

## 📋 Bot 使用命令

发送 `/start` 给你的 Bot 打开主菜单。

### 图床
- 直接**发送图片**给 Bot → 自动保存并回复公开链接
- `/images` 查看最近上传的图片列表

### 记事本
- `/addnote` → 按提示输入标题和内容
- `/notes` → 查看所有记事本（支持编辑/删除按钮）
- `/delnote <ID>` 快速删除

### 收藏夹
- `/addbookmark <URL> [备注]` 
- `/bookmarks` → 查看所有收藏（支持编辑/删除）
- `/delbookmark <ID>`

### 备份管理
- `/backup` → 立即执行 WebDAV 备份
- `/export` → 导出当前数据为 zip 文件（通过 Telegram 发送）
- 上传 zip 文件给 Bot → 自动导入恢复数据

## 🛠️ 开发与 GitHub 自动构建

### 本地开发

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
```

### GitHub Actions 自动构建 Docker 镜像

项目已配置 `.github/workflows/docker-publish.yml`

**首次设置：**

1. 在 GitHub 仓库 Settings → Secrets and variables → Actions 添加：
   - `DOCKERHUB_USERNAME`：你的 Docker Hub 用户名
   - `DOCKERHUB_TOKEN`：Docker Hub Access Token（在 Docker Hub → Account Settings → Security 创建）

2. 推送代码到 `main` 分支，Actions 会自动：
   - 构建 Docker 镜像
   - 推送到 `你的DockerHub用户名/telegram-bot-tool:latest`

### Docker Hub 镜像

镜像地址：`你的用户名/telegram-bot-tool`

运行示例：

```bash
docker run -d \
  --name telegram-bot \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  你的用户名/telegram-bot-tool
```

## 📁 项目结构

```
telegram-bot-tool/
├── bot.py                 # 主程序入口 + Bot 逻辑
├── web.py                 # Flask Web 服务器（图床图片服务）
├── database.py            # SQLite 数据库操作
├── webdav_backup.py       # WebDAV 备份/恢复逻辑
├── config.py              # 配置加载
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .github/workflows/
│   └── docker-publish.yml
├── data/                  # 数据目录（自动创建）
│   ├── bot.db
│   └── images/
└── README.md
```

## 🔒 安全建议

- 仅允许 `OWNER_CHAT_ID` 使用 Bot（已实现）
- 生产环境建议使用 HTTPS + 域名
- WebDAV 密码请妥善保管
- 定期备份重要数据

## ❓ 常见问题

**Q: 图床链接打不开？**  
A: 检查 `PUBLIC_BASE_URL` 是否正确配置，并确保域名已正确反向代理到容器的 8080 端口。

**Q: 如何修改 Bot 命令？**  
A: 编辑 `bot.py` 中的命令处理器。

**Q: 支持多用户吗？**  
A: 当前为单用户设计（通过 OWNER_CHAT_ID 限制）。如需多用户可扩展权限系统。

**Q: 图片存储位置？**  
A: Docker 卷 `data/images/`，可随时迁移。

## 📄 License

MIT License

---

**享受你的个人 Telegram 工具箱！** 如有问题欢迎提 Issue 或 PR。