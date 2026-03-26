# DigitalEmployeeMemo 用户使用手册

## 系统概述

DigitalEmployeeMemo 是一个企业跨部门协作任务管理系统，主要功能包括：
- **任务管理** - 领导创建任务/项目，分配牵头部门和预期交付物
- **工作分配** - 牵头部门注册各部门的协作任务分配
- **部门反馈** - 各部门提供反馈（同意/不同意/需要讨论）
- **冲突上报** - 牵头部门上报协调冲突，系统自动生成领导备忘录
- **领导备忘录** - 领导查看待处理/已解决的冲突报告并做出决策
- **智能提醒** - 多阶段提醒机制，支持升级处理

---

## 访问系统

### 基础信息

| 服务 | 地址 |
|------|------|
| API 地址 | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

### Docker 容器状态

所有服务正常运行时：
```
$ docker ps
CONTAINER ID   IMAGE                STATUS
dem_api        digitalemployeememo  Up (healthy)   0.0.0.0:8000->8000/tcp
dem_db         postgres:15-alpine   Up (healthy)    0.0.0.0:5432->5432/tcp
dem_redis      redis:7-alpine      Up (healthy)    0.0.0.0:6379->6379/tcp
dem_celery_worker                  Up              8000/tcp
dem_celery_beat                   Up              8000/tcp
```

---

## 认证方式

系统使用 Header 认证，请求时需要在 HTTP 头中携带：

```
X-User-ID: <用户ID>
X-Dept-ID: <部门ID>
```

示例（使用 curl）：
```bash
curl -H "X-User-ID: 1" -H "X-Dept-ID: 1" http://localhost:8000/api/v1/tasks
```

---

## API 详细使用指南

### 1. 任务管理 (Tasks)

#### 创建任务
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "title": "开发新版官网",
    "description": "需要与市场部协作完成新版官网开发",
    "deadline": "2026-04-15T00:00:00",
    "priority": "high",
    "deliverables": ["网站原型", "前端代码", "后台API"],
    "lead_dept_id": 1
  }'
```

#### 获取任务列表
```bash
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取单个任务
```bash
curl -X GET http://localhost:8000/api/v1/tasks/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 更新任务
```bash
curl -X PUT http://localhost:8000/api/v1/tasks/1 \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "title": "开发新版官网v2",
    "status": "in_progress"
  }'
```

#### 删除任务
```bash
curl -X DELETE http://localhost:8000/api/v1/tasks/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

---

### 2. 工作分配 (Assignments)

任务创建后，牵头部门需要为参与协作的部门注册分配任务。

#### 创建分配
```bash
curl -X POST http://localhost:8000/api/v1/assignments/tasks/1/assignments \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "dept_id": 2,
    "assigned_tasks": "负责前端页面开发",
    "deadline": "2026-04-10T00:00:00",
    "dependencies": [],
    "resources_needed": ["2名前端工程师"]
  }'
```

#### 获取任务的分配列表
```bash
curl -X GET http://localhost:8000/api/v1/assignments/tasks/1/assignments \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取单个分配
```bash
curl -X GET http://localhost:8000/api/v1/assignments/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 更新分配
```bash
curl -X PUT http://localhost:8000/api/v1/assignments/1 \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "status": "completed",
    "completion_notes": "已完成前端开发"
  }'
```

---

### 3. 部门反馈 (Feedbacks)

各部门收到任务分配后，需要提供反馈意见。

#### 提交反馈
```bash
curl -X POST http://localhost:8000/api/v1/feedbacks/assignments/1/feedback \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 2" \
  -H "X-Dept-ID: 2" \
  -d '{
    "feedback_type": "agree",
    "reason": "同意接受此任务分配",
    "proposed_changes": null,
    "attachments": []
  }'

# 反馈类型可选：
# - agree: 同意
# - disagree: 不同意
# - need_discussion: 需要讨论
```

#### 获取分配的反馈列表
```bash
curl -X GET http://localhost:8000/api/v1/feedbacks/assignments/1/feedbacks \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取我的反馈
```bash
curl -X GET http://localhost:8000/api/v1/feedbacks/feedbacks/my \
  -H "X-User-ID: 2" \
  -H "X-Dept-ID: 2"
```

---

### 4. 冲突上报 (Conflicts)

当任务执行过程中出现协调冲突时，牵头部门可以上报冲突。

#### 上报冲突
```bash
curl -X POST http://localhost:8000/api/v1/conflicts \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "conflict_summary": "市场部与研发部在官网设计稿上存在分歧",
    "conflict_details": {
      "market_dept": "需要全新视觉设计",
      "rd_dept": "现有技术架构限制，无法实现某些效果"
    },
    "proposed_solutions": ["折中方案：简化设计", "技术评估后再定"],
    "urgency_level": "high",
    "need_decision_by": "2026-03-28T00:00:00",
    "task_id": 1
  }'

# 紧急程度可选：low, medium, high, critical
```

#### 获取冲突列表
```bash
curl -X GET http://localhost:8000/api/v1/conflicts \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取单个冲突
```bash
curl -X GET http://localhost:8000/api/v1/conflicts/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 做出决策
```bash
curl -X POST http://localhost:8000/api/v1/conflicts/1/decision \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "decision": "approved",
    "decision_notes": "采用折中方案，简化设计但保留核心交互效果",
    "implementation_notes": "由研发部主导设计评审会议"
  }'

# 决策可选：approved, rejected, escalated
```

#### 升级冲突
```bash
curl -X POST http://localhost:8000/api/v1/conflicts/1/escalate \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "escalation_reason": "部门无法达成一致，需要更高级别决策",
    "escalate_to": "secretary"
  }'
```

---

### 5. 领导备忘录 (Memos)

冲突上报后，系统会自动生成领导备忘录。

#### 获取待处理备忘录
```bash
curl -X GET http://localhost:8000/api/v1/memos/leader/pending \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取所有备忘录
```bash
curl -X GET http://localhost:8000/api/v1/memos \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取单个备忘录
```bash
curl -X GET http://localhost:8000/api/v1/memos/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 更新备忘录阅读状态
```bash
curl -X PUT http://localhost:8000/api/v1/memos/1/read-status \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "is_read": true
  }'
```

#### 备忘录决策
```bash
curl -X POST http://localhost:8000/api/v1/memos/1/decision \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1" \
  -d '{
    "decision": "approved",
    "decision_notes": "同意折中方案"
  }'
```

---

### 6. 领导仪表盘 (Dashboard)

获取统计摘要和概览信息。

#### 获取仪表盘摘要
```bash
curl -X GET http://localhost:8000/api/v1/leader/dashboard \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

返回示例：
```json
{
  "total_tasks": 10,
  "pending_tasks": 3,
  "in_progress_tasks": 5,
  "completed_tasks": 2,
  "total_conflicts": 2,
  "pending_conflicts": 1,
  "resolved_conflicts": 1,
  "total_memos": 3,
  "unread_memos": 1
}
```

---

### 7. 提醒 (Reminders)

#### 获取提醒列表
```bash
curl -X GET http://localhost:8000/api/v1/reminders \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 获取单个提醒
```bash
curl -X GET http://localhost:8000/api/v1/reminders/1 \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

#### 测试提醒（仅开发环境）
```bash
curl -X POST http://localhost:8000/api/v1/reminders/test \
  -H "X-User-ID: 1" \
  -H "X-Dept-ID: 1"
```

---

## 典型工作流程

### 场景：跨部门任务协作

```
1. 领导创建任务
   POST /api/v1/tasks
   → 任务ID: 1

2. 牵头部门注册分配
   POST /api/v1/assignments/tasks/1/assignments
   → 分配ID: 1

3. 参与部门提交反馈
   POST /api/v1/feedbacks/assignments/1/feedback
   → 反馈已提交

4. 如有冲突，牵头部门上报
   POST /api/v1/conflicts
   → 冲突已创建，生成备忘录

5. 领导查看待处理备忘录
   GET /api/v1/memos/leader/pending

6. 领导做出决策
   POST /api/v1/conflicts/{id}/decision
   → 冲突已解决

7. 系统发送升级提醒（如需要）
   → 2小时后自动提醒
   → 24小时后邮件提醒
   → 48小时后微信提醒
   → 72小时后升级处理
```

---

## 提醒策略

| 阶段 | 触发时间 | 提醒方式 |
|------|----------|----------|
| 立即 | 上报时 | 应用内通知 |
| 2小时 | 2小时未读 | 应用内 + 邮件 |
| 24小时 | 24小时未读 | 应用内 + 邮件 |
| 48小时 | 48小时未读 | 应用内 + 邮件 + 微信 |
| 72小时 | 72小时未读 | 全部方式 + 升级至秘书 |

---

## 健康检查

检查服务状态：
```bash
curl http://localhost:8000/health
```

返回：
```json
{"status":"healthy","service":"DigitalEmployeeMemo API","version":"1.0.0"}
```

---

## 常见问题

### 1. 容器无法启动
```bash
# 检查容器状态
docker ps -a

# 查看日志
docker-compose logs api
docker-compose logs celery_worker

# 重启服务
docker-compose restart
```

### 2. 数据库连接失败
```bash
# 检查数据库容器
docker-compose logs db

# 等待数据库就绪
docker-compose up -d db
```

### 3. Celery 任务未执行
```bash
# 检查 worker 状态
docker-compose logs celery_worker

# 检查 beat 状态
docker-compose logs celery_beat

# 重启 worker
docker-compose restart celery_worker celery_beat
```

### 4. API 返回认证错误
确保请求头中包含正确的 `X-User-ID` 和 `X-Dept-ID`。

---

## 环境变量配置

部署环境中的实际配置（docker-compose.yml）：

| 变量 | 值 | 说明 |
|------|-----|------|
| DATABASE_URL | postgresql+asyncpg://... | 异步数据库连接 |
| DATABASE_URL_SYNC | postgresql://... | 同步数据库连接 |
| REDIS_URL | redis://redis:6379/0 | Redis 连接 |
| CELERY_BROKER_URL | redis://redis:6379/0 | Celery 消息队列 |
| CELERY_BACKEND_URL | redis://redis:6379/0 | Celery 结果存储 |
| DEBUG | true | 调试模式 |
| NOTIFICATION_EMAIL_ENABLED | false | 邮件通知（未启用） |

---

## 技术架构

- **Web 框架**: FastAPI (异步)
- **ORM**: SQLAlchemy 2.0+ (异步)
- **数据库**: PostgreSQL 15
- **缓存/消息队列**: Redis 7
- **任务队列**: Celery 5.3.6
- **数据库迁移**: Alembic

---

## 许可证

MIT License
