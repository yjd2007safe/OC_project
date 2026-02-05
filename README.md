# CalendarSecretary

CalendarSecretary 是一个轻量级日程管理 Web 应用，支持 Web 登录与 API Key 认证，适合个人或 AI 助手使用。

## 功能

- 日程的增删改查（标题、时间、地点、描述）
- JSON 文件存储（每个用户独立日程文件）
- 双认证方式：
  - Web 登录：用户名/密码 + Session
  - API 登录：Header 传递 API Key
- 密码采用 PBKDF2 哈希存储

## 项目结构

```
.
├── app.py
├── data
│   ├── users.json
│   └── schedules
├── static
│   ├── script.js
│   └── style.css
├── templates
│   └── index.html
└── README.md
```

## 快速开始

1. 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install flask
```

2. 启动服务：

```bash
python app.py
```

3. 访问应用：

- Web 页面：http://localhost:5000
- 健康检查：http://localhost:5000/health

## 示例账号

| 用户名 | 密码 | API Key |
| --- | --- | --- |
| demo | demo123 | cs_demo_key_001 |
| admin | admin123 | cs_admin_key_002 |

## API 使用示例

### 获取日程列表

```bash
curl -H "X-API-Key: cs_demo_key_001" http://localhost:5000/api/schedules
```

### 新建日程

```bash
curl -X POST http://localhost:5000/api/schedules \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cs_demo_key_001" \
  -d '{"title":"会议","time":"2024-04-01T10:00","location":"会议室","description":"季度复盘"}'
```

### 更新日程

```bash
curl -X PUT http://localhost:5000/api/schedules/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cs_demo_key_001" \
  -d '{"location":"线上","description":"改为线上会议"}'
```

### 删除日程

```bash
curl -X DELETE http://localhost:5000/api/schedules/1 \
  -H "X-API-Key: cs_demo_key_001"
```

## 说明

- 用户信息存储在 `data/users.json`。
- 日程数据存储在 `data/schedules/<username>.json`。
- 若需新增用户，可参照 `users.json` 结构生成 PBKDF2 哈希。
