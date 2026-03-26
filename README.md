# 数字员工备忘录系统

多账户备忘录后台服务，每个账户的备忘录独立存储在 xlsx 文件中。

## 功能特性

- 多账户支持，每个账户数据隔离存储
- 完整的 CRUD 操作（创建、读取、更新、删除）
- **跨用户留言**：可以给其他用户发送备忘录，标题自动添加 `[给{收件人}]` 前缀
- 数据存储为 xlsx 格式，便于查看和编辑
- RESTful API，通过 curl 即可调用

## 技术栈

- Python 3.x + Flask
- openpyxl（xlsx 文件处理）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

服务启动后访问 http://localhost:5001

## API 接口

| 方法   | 接口                                              | 说明         |
|--------|---------------------------------------------------|--------------|
| POST   | `/api/accounts/{账户名}/memos`                     | 创建备忘录   |
| GET    | `/api/accounts/{账户名}/memos`                     | 获取所有备忘录 |
| GET    | `/api/accounts/{账户名}/memos/{备忘录ID}`           | 获取单条备忘录 |
| PUT    | `/api/accounts/{账户名}/memos/{备忘录ID}`           | 更新备忘录   |
| DELETE | `/api/accounts/{账户名}/memos/{备忘录ID}`           | 删除备忘录   |

## 使用示例

### 创建备忘录
```bash
curl -X POST http://localhost:5001/api/accounts/张三/memos \
  -H "Content-Type: application/json" \
  -d '{"title": "会议记录", "content": "讨论Q1目标"}'
```

### 跨用户留言
```bash
curl -X POST http://localhost:5001/api/accounts/张三/memos \
  -H "Content-Type: application/json" \
  -d '{"title": "明天下午会议", "content": "讨论项目进度", "to": "小翁"}'
```
- 备忘录会存储在**收件人**的文件中
- 标题自动添加 `[给小翁]` 前缀
- 返回数据中包含 `from` 字段表示发件人

### 获取所有备忘录
```bash
curl http://localhost:5001/api/accounts/张三/memos
```

### 获取单条备忘录
```bash
curl http://localhost:5001/api/accounts/张三/memos/{备忘录ID}
```

### 更新备忘录
```bash
curl -X PUT http://localhost:5001/api/accounts/张三/memos/{备忘录ID} \
  -H "Content-Type: application/json" \
  -d '{"title": "更新后的标题", "content": "新内容"}'
```

### 删除备忘录
```bash
curl -X DELETE http://localhost:5001/api/accounts/张三/memos/{备忘录ID}
```

## 数据存储

每个账户的备忘录存储在 `data/{账户名}.xlsx` 文件中。

## 响应格式

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "标题",
    "content": "内容",
    "created_at": "创建时间",
    "updated_at": "更新时间"
  }
}
```

错误响应：
```json
{
  "success": false,
  "error": "错误信息"
}
```
