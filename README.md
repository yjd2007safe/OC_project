# CalendarSecretary

CalendarSecretary 是一个轻量级日程管理 Web 应用，支持 Web 登录与 API Key 认证，适合个人或 AI 助手使用。

## 功能

- 用户认证：登录、会话保持、API Key 认证
- 用户注册：`/api/register`（用户名与密码规则校验、自动生成 API Key）
- 日程管理：新增、查询、更新、删除
- 重复日程：支持 daily / weekly / monthly / yearly 频率
- 重复结束方式：never / until / count
- 工作日/休息日提醒：支持日期类型查询与创建日程提醒
- PostgreSQL/Supabase 存储（兼容本地 SQLite 开发）
- 管理后台：用户管理、系统统计、账户启用/禁用、重置密码
- 密码采用 PBKDF2-SHA256 哈希存储

## 项目结构

```
.
├── app.py
├── migrations
│   └── schema.sql
├── scripts
│   └── init_db.py
├── static
│   ├── script.js
│   ├── admin.js
│   └── style.css
├── templates
│   ├── index.html
│   └── admin.html
└── README.md
```

## 快速开始

1. 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


2. 配置环境变量（可复制 `.env.example`）：

```bash
cp .env.example .env
# 至少设置 DATABASE_URL
```

3. 初始化数据库：

```bash
python scripts/init_db.py
```

4. 启动服务：

```bash
python app.py
```

5. 访问应用：

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


### 查询日期时间工作状态

```bash
curl -H "X-API-Key: cs_demo_key_001" \
  "http://localhost:5000/api/events/workday-check?datetime=2025-02-10T12:30"
```

返回示例：

```json
{
  "datetime": "2025-02-10T12:30",
  "is_workday": true,
  "is_working_hours": false,
  "work_period": null,
  "day_type": "workday_lunch",
  "description": "午休时间"
}
```

> 创建日程时，若时间位于午休（12:00-13:30）、工作日非工作时段（09:00前或18:00后）或周末，接口会在返回体中附加 `warning` 字段并给出对应提示。

### 智能匹配空闲时段并自动创建日程

```bash
curl -X POST http://localhost:5000/api/slots/find-and-book \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cs_demo_key_001" \
  -d '{
    "target_date": "2025-02-10",
    "duration_hours": 1.5,
    "title": "客户沟通",
    "location": "线上",
    "description": "产品需求确认",
    "preferred_start_time": "09:00",
    "preferred_end_time": "18:00"
  }'
```

> `duration_hours` 支持小数（例如 `1.5` 表示 1 小时 30 分钟）；`preferred_start_time` / `preferred_end_time` 可选，默认全天范围。

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

## 存储与部署说明

- 用户与日程数据统一存储在数据库表 `users` / `events`。
- 通过 `DATABASE_URL` 连接数据库；生产（Vercel）推荐使用 Supabase Postgres。
- 当缺少数据库配置时，API 返回 JSON 错误（`503` + `database_not_configured`），不会返回 500 HTML。
- 初始化或迁移可执行：`python scripts/init_db.py`。
- 为兼容旧客户端，`/api/schedules` 仍可用，并与 `/api/events` 共享逻辑。

### Vercel 部署（Supabase）

1. 在 Supabase 创建项目并获取：`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、Postgres `DATABASE_URL`。
2. 在 Vercel Project Settings → Environment Variables 中配置上述变量与 `CALENDAR_SECRET_KEY`。
3. 部署前执行一次 schema 初始化（本地或 CI）：

```bash
python scripts/init_db.py
```

4. 部署后访问 `/health` 验证实例可用。


## 管理员功能

- 管理员用户名固定为 `admin`，访问 `/admin` 时会校验管理员身份，非管理员自动重定向到首页。
- 所有 `/api/admin/*` 接口均要求管理员会话或管理员 API Key。

### 管理接口

#### 获取用户列表

```bash
curl -H "X-API-Key: cs_admin_key_002" http://localhost:5000/api/admin/users
```

#### 删除用户

```bash
curl -X DELETE -H "X-API-Key: cs_admin_key_002" \
  http://localhost:5000/api/admin/users/testuser
```

#### 重置用户密码

```bash
curl -X POST -H "X-API-Key: cs_admin_key_002" \
  -H "Content-Type: application/json" \
  -d '{"new_password":"NewPass123"}' \
  http://localhost:5000/api/admin/users/testuser/reset-password
```

#### 启用/禁用用户

```bash
curl -X POST -H "X-API-Key: cs_admin_key_002" \
  http://localhost:5000/api/admin/users/testuser/toggle
```

#### 获取系统统计

```bash
curl -H "X-API-Key: cs_admin_key_002" http://localhost:5000/api/admin/stats
```
