# CalendarSecretary

CalendarSecretary 是一个轻量级日程管理 Web 应用，支持 Web 登录与 API Key 认证，适合个人或 AI 助手使用。

## 功能

- 用户认证：登录、会话保持、API Key 认证
- 用户注册：`/api/register`（用户名与密码规则校验、自动生成 API Key）
- 日程管理：新增、查询、更新、删除
- 多视图日历：支持日/周/月视图切换，支持上一页/下一页/回到今天导航
- 视图记忆：自动记住上次选择的视图（localStorage）
- 重复日程：支持 daily / weekly / monthly / yearly 频率
- 重复结束方式：never / until / count
- 工作日/休息日提醒：支持日期类型查询与创建日程提醒
- JSON 文件存储（每个用户独立日程文件）
- 管理后台：用户管理、系统统计、账户启用/禁用、重置密码
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
pip install flask
```

2. 启动服务：

```bash
python app.py
```

3. 访问应用：

- Web 页面：http://localhost:5000
- 健康检查：http://localhost:5000/health


## Web 端视图说明

登录后右侧面板支持 **日 / 周 / 月** 三种视图：

- **日视图**：查看当天完整日程列表，可直接编辑/删除。
- **周视图**：按周一到周日展示每日日程摘要。
- **月视图**：以月历网格展示整月日期，每天显示日程摘要或数量。

导航按钮支持：

- `上一页`：按当前视图粒度前进（天/周/月）
- `下一页`：按当前视图粒度后退（天/周/月）
- `今天`：快速回到当前日期

系统会在浏览器 `localStorage` 中保存上一次使用的视图模式，下次登录时自动恢复。

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

## 说明

- 用户信息存储在 `data/users.json`。
- 日程数据存储在 `data/schedules/<username>.json`。
- 为兼容旧客户端，`/api/schedules` 仍可用，并与 `/api/events` 共享逻辑。


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
