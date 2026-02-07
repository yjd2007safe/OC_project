# CalendarSecretary

CalendarSecretary 是一个轻量级日程管理 Web 应用，支持 Web 登录与 API Key 认证，适合个人或 AI 助手使用。

## 功能

- 用户认证：登录、会话保持、API Key 认证
- 用户注册：`/api/register`（用户名与密码规则校验、自动生成 API Key）
- 日程管理：新增、查询、更新、删除
- 重复日程：支持 daily / weekly / monthly / yearly 频率
- 重复结束方式：never / until / count
- JSON 文件存储（每个用户独立日程文件）
- 密码采用 PBKDF2-SHA256 哈希存储

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

### 注册用户

```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"new_user","password":"pass12345"}'
```

> 用户名必须为 4-20 位字母/数字/下划线；密码至少 8 位且包含字母和数字。

### 获取日程列表

```bash
curl -H "X-API-Key: cs_demo_key_001" http://localhost:5000/api/events
```

### 获取展开后的重复日程

```bash
curl -H "X-API-Key: cs_demo_key_001" \
  "http://localhost:5000/api/events?expand=1&start=2025-01-01T00:00&end=2025-12-31T23:59"
```

### 新建日程（含重复规则）

```bash
curl -X POST http://localhost:5000/api/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cs_demo_key_001" \
  -d '{
    "title": "团队例会",
    "time": "2025-02-10T14:00",
    "location": "会议室 A",
    "description": "周会",
    "recurrence": {
      "frequency": "weekly",
      "end_type": "count",
      "count": 10
    }
  }'
```

### 更新日程

```bash
curl -X PUT http://localhost:5000/api/events/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cs_demo_key_001" \
  -d '{"location":"线上","description":"改为线上会议"}'
```

### 删除日程

```bash
curl -X DELETE http://localhost:5000/api/events/1 \
  -H "X-API-Key: cs_demo_key_001"
```

## 说明

- 用户信息存储在 `data/users.json`。
- 日程数据存储在 `data/schedules/<username>.json`。
- 为兼容旧客户端，`/api/schedules` 仍可用，并与 `/api/events` 共享逻辑。
