# CalendarSecretary - 项目助手指南

## 项目概述

**项目名称**: CalendarSecretary  
**类型**: 日程管理 Web 应用  
**技术栈**: Python 3.14 + Flask + JSON 文件存储  
**架构**: 单体应用，前后端不分离

## 功能特性

### 已实现功能

1. **用户认证**
   - Web Session 登录（用户名/密码）
   - API Key 认证（供外部调用）
   - PBKDF2-SHA256 密码加密

2. **日程管理**
   - 创建日程（标题、时间、地点、描述）
   - 查看日程列表（支持日期筛选）
   - 查看单个日程详情
   - 更新日程
   - 删除日程

3. **数据存储**
   - 用户数据: `data/users.json`
   - 日程数据: `data/schedules/{username}.json`
   - 原子写入，防止数据损坏

4. **Web 界面**
   - 登录页面
   - 日程管理主界面
   - 添加/编辑日程表单
   - 日期筛选功能

5. **API 接口**
   - RESTful API 设计
   - X-API-Key 请求头认证
   - 支持 CRUD 操作

## 目录结构

```
CalendarSecretary/
├── app.py                 # Flask 主程序（后端逻辑）
├── README.md              # 项目说明文档
├── data/                  # 数据目录
│   ├── users.json         # 用户数据
│   └── schedules/         # 用户日程文件
├── templates/             # HTML 模板
│   └── index.html         # 单页应用主页面
└── static/                # 静态资源
    ├── style.css          # 样式文件
    └── script.js          # 前端脚本
```

## 编码规范

### Python
- 使用 4 空格缩进
- 函数命名: snake_case
- 类命名: PascalCase
- 常量: UPPER_CASE
- 类型提示: 函数参数和返回值使用类型注解

### API 设计
- 路由前缀: `/api/`
- 认证头: `X-API-Key`
- 响应格式: JSON
- 状态码: 200 成功, 201 创建, 400 请求错误, 401 未授权, 404 不存在

### 前端
- 原生 JavaScript（无框架）
- CSS 命名: kebab-case
- DOM 操作使用原生 API

## 开发工作流程

### 运行应用
```bash
python app.py
# 访问 http://127.0.0.1:5000
```

### 默认账号
- 用户名: `demo` / 密码: `password123` / API Key: `cs_demo_key_001`
- 用户名: `admin` / 密码: `adminpass` / API Key: `cs_admin_key_002`

### API 调用示例
```bash
# 获取日程
curl -H "X-API-Key: cs_demo_key_001" \
     http://127.0.0.1:5000/api/events

# 创建日程
curl -X POST \
     -H "X-API-Key: cs_demo_key_001" \
     -H "Content-Type: application/json" \
     -d '{"title":"会议","datetime":"2025-02-10 14:00"}' \
     http://127.0.0.1:5000/api/events
```

## 扩展建议

### 待实现功能
1. **数据库迁移**: 从 JSON 文件迁移到 SQLite/PostgreSQL
2. **用户注册**: 目前只支持预设账号
3. **日程提醒**: 邮件/推送通知
4. **重复日程**: 支持周期性事件
5. **权限管理**: 角色区分（管理员/普通用户）
6. **数据导入导出**: 支持 iCal/CSV 格式
7. **前端框架**: 可迁移到 Vue/React

### 安全增强
1. 生产环境修改 `SECRET_KEY`
2. 添加速率限制（Rate Limiting）
3. HTTPS 强制
4. 输入数据验证增强

## 依赖

```
flask>=3.0.0
```

## 注意事项

1. **数据持久化**: 当前使用 JSON 文件存储，适合小型应用
2. **并发**: 文件锁机制简单，高并发场景建议用数据库
3. **备份**: 定期备份 `data/` 目录
4. **环境变量**: 生产环境设置 `SECRET_KEY`
