---
name: digital-employee-memo
description: DigitalEmployeeMemo system - cross-department task management with conflict resolution workflow
---

# DigitalEmployeeMemo System Skill

## System Overview

DigitalEmployeeMemo 是一个企业跨部门协作任务管理系统，主要功能包括：

- **任务管理** - 领导创建任务/项目，分配牵头部门和预期交付物
- **工作分配** - 牵头部门注册各部门的协作任务分配
- **部门反馈** - 各部门提供反馈（同意/不同意/需要讨论）
- **冲突上报** - 牵头部门上报协调冲突，系统自动生成领导备忘录
- **领导备忘录** - 领导查看待处理/已解决的冲突报告并做出决策
- **智能提醒** - 多阶段提醒机制，支持升级处理

## User Roles

| 角色 | 英文 | 权限 |
|------|------|------|
| 领导 | leader | 创建任务、查看所有数据、解决冲突 |
| 部门负责人 | dept_head | 分解任务、上报冲突 |
| 部门成员 | member | 提交反馈、查看任务 |

## Typical Workflow

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
```

## API Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Header 认证：
```
X-User-ID: <用户ID>
X-Dept-ID: <部门ID>
```

## Key Endpoints

| 功能 | 方法 | 路径 |
|------|------|------|
| 创建任务 | POST | /tasks |
| 任务列表 | GET | /tasks |
| 创建分配 | POST | /assignments/tasks/{task_id}/assignments |
| 提交反馈 | POST | /feedbacks/assignments/{assignment_id}/feedback |
| 上报冲突 | POST | /conflicts |
| 冲突决策 | POST | /conflicts/{id}/decision |
| 领导待处理备忘录 | GET | /memos/leader/pending |
| 领导面板 | GET | /leader/dashboard |

## Common Issues & Solutions

### MissingGreenlet Error

**症状**: Pydantic 验证时出现 `MissingGreenlet: greenlet_spawn has not been called`

**原因**: SQLAlchemy 异步对象在过期状态时被访问，触发了懒加载

**解决**:
1. 在 flush() 后添加 `await db.refresh(obj)`
2. 避免使用 `obj.relationship` 访问，改用 `obj.foreign_key_id` 直接访问
3. 如果需要关联数据，使用显式查询 `await db.execute(select(Model).where(...))`

### Timezone Error

**症状**: `can't compare offset-naive and offset-aware datetimes`

**解决**: 使用 `datetime.now(timezone.utc)` 替代 `datetime.utcnow()`，并确保 `today_start` 没有 timezone 信息

### Schema Validation Error

**症状**: `Input should be a valid dictionary` 对于 list 类型字段

**原因**: Pydantic schema 定义类型与实际数据不匹配

**解决**: 确认 schema 中使用 `List[Dict]` 而非 `Dict` 用于列表类型

## Database Models

- **Task** - 任务
- **Assignment** - 工作分配
- **Feedback** - 部门反馈
- **ConflictReport** - 冲突报告
- **Memo** - 领导备忘录
- **Reminder** - 提醒记录
- **User** - 用户
- **Department** - 部门
