---
name: digital-employee-memo
description: DigitalEmployeeMemo - simplified bidirectional message memo system
---

# DigitalEmployeeMemo System Skill

## System Overview

DigitalEmployeeMemo 是一个简化的双向留言备忘录系统，支持领导和员工互相发送消息。

## User Roles

| 角色 | 英文 | 权限 |
|------|------|------|
| 领导 | leader | 可以给任何人发消息 |
| 部门负责人 | dept_head | 只能给领导发消息 |
| 部门成员 | member | 只能给领导发消息 |

## Authentication

Header 认证：
```
X-User-ID: <用户ID>
X-Dept-ID: <部门ID>
```

## API Base URL

```
http://localhost:8000/api/v1
```

## API Endpoints

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /messages | 发送留言 |
| GET | /messages | 获取消息列表（支持 direction=sent/received） |
| GET | /messages/{id} | 获取单条消息详情 |
| PUT | /messages/{id}/read | 标记已读 |
| DELETE | /messages/{id} | 删除消息（仅发送者可删除） |

## Usage Examples

### 发送消息

领导发送给员工：
```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{"title": "通知", "content": "请注意查收", "receiver_id": 2}'
```

员工发送给领导：
```bash
curl -X POST http://localhost:8000/api/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 2" \
  -H "X-Dept-ID: 2" \
  -d '{"title": "反馈", "content": "已完成任务", "receiver_id": 1}'
```

### 获取消息列表

```bash
# 获取所有消息
curl -X GET http://localhost:8000/api/v1/messages \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"

# 仅获取发送的消息
curl -X GET "http://localhost:8000/api/v1/messages?direction=sent" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"

# 仅获取接收的消息
curl -X GET "http://localhost:8000/api/v1/messages?direction=received" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

### 标记已读

```bash
curl -X PUT http://localhost:8000/api/v1/messages/1/read \
  -H "X-User-ID: 2" \
  -H "X-Dept-ID: 2"
```

### 获取单条消息

```bash
curl -X GET http://localhost:8000/api/v1/messages/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

## Common Issues & Solutions

### MissingGreenlet Error

**症状**: Pydantic 验证时出现 `MissingGreenlet: greenlet_spawn has not been called`

**原因**: SQLAlchemy 异步对象在过期状态时被访问

**解决**: 在 flush() 后添加 `await db.refresh(obj)`

### Schema Validation Error

**症状**: 类型验证失败

**解决**: 确保请求体中的字段类型与 schema 匹配

## Database Models

- **User** - 用户（id, name, email, role, dept_id）
- **Department** - 部门（id, name, description）
- **Message** - 留言（id, sender_id, receiver_id, title, content, is_read, read_at）

## Deployment

```bash
# 启动服务
docker-compose up -d

# 运行迁移
docker-compose exec alembic sh -c "cd /app && alembic upgrade head"

# 初始化种子数据
docker-compose run --rm api python seed_data.py
```

## Health Check

```bash
curl http://localhost:8000/health
```
