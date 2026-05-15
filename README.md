# Telegram Bot Tool

一个模块化、可维护的 Telegram 多工具机器人（支持 Docker 一键部署）

## ✨ 功能列表

| 命令     | 功能           | 说明                              |
|----------|----------------|-----------------------------------|
| `/tool1` | 笔记本功能     | 添加笔记、查看笔记、按序号删除    |
| `/tool2` | 图床功能       | 上传图片 → 获取 URL / HTML / BBCode / Markdown 链接 |
| `/tool3` | 备份功能       | 导出/导入 JSON + 一键 WebDAV 备份 |

## 🚀 快速开始

### 1. 获取必要信息

- **Bot Token**：[@BotFather](https://t.me/BotFather)
- **图床 Token**（可选但推荐）：[sm.ms API Token](https://sm.ms/)
- **WebDAV**（备份功能需要）：坚果云、Alist、Nextcloud 等

### 2. 使用 Docker Compose 部署（推荐）

```bash
# 1. 克隆或下载项目
git clone https://github.com/你的用户名/telegram-bot-tool.git
cd telegram-bot-tool

# 2. 配置环境变量
cp .env.example .env
nano .env          # 填入 BOT_TOKEN（必须），SMMS_TOKEN 和 WebDAV 配置（可选）

# 3. 启动
docker compose up -d --build

# 查看日志
docker compose logs -f
```

### 3. 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入配置
python -m bot.main
```

## 📁 项目结构

```
telegram-bot-tool/
├── bot/
│   ├── handlers/
│   │   ├── common.py      # /start /help
│   │   ├── tool1.py       # 笔记本
│   │   ├── tool2.py       # 图床
│   │   └── tool3.py       # 备份
│   ├── database.py
│   ├── config.py
│   └── main.py
├── data/                  # 持久化数据库（自动创建）
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 配置说明（.env）

```env
BOT_TOKEN=xxxxxxxxxx

# 图床（sm.ms）
SMMS_TOKEN=xxxxxxxxxx

# WebDAV 备份
WEBDAV_URL=https://dav.example.com/backup/
WEBDAV_USERNAME=xxx
WEBDAV_PASSWORD=xxx
```

## 📦 备份功能说明

- **导出文件**：导出所有笔记 + 图床记录为 JSON
- **导入文件**：上传 JSON 恢复数据
- **立即备份**：一键上传备份文件到你的 WebDAV

---

**项目已全部完成**，三个工具全部可用，直接上传 GitHub 即可使用！