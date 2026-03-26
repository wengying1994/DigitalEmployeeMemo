# 备忘录技能

数字员工备忘录系统的 Claude Code 集成技能。

## 系统信息

备忘录后端服务运行在 `http://localhost:5001`，每个账户的备忘录存储在 `data/{账户名}.xlsx` 文件中。

## 命令

### 添加备忘录
添加新的备忘录到指定账户。

```
/memo add <账户> <标题> [内容]
```

**示例：**
```
/memo add 张三 下周二出差 下周二去合肥开会
/memo add 小翁 团队会议 每周三下午2点
```

### 跨用户留言
给其他用户发送备忘录，备忘录会存储在收件人账户中。

```
/memo send <发件人> <收件人> <标题> [内容]
```

**示例：**
```
/memo send 张三 小翁 明天下午会议 讨论项目进度
/memo send 小翁 张三 周五总结 本周完成的工作
```

### 查看备忘录
获取指定账户的所有备忘录。

```
/memo list <账户>
```

**示例：**
```
/memo list 张三
/memo list 小翁
```

### 搜索备忘录
根据关键词搜索备忘录内容。

```
/memo search <账户> <关键词>
```

**示例：**
```
/memo search 张三 出差
/memo search 小翁 会议
```

### 删除备忘录
删除指定账户的某条备忘录。

```
/memo delete <账户> <备忘录ID>
```

**示例：**
```
/memo delete 张三 4f32cfea-bb80-4232-944d-031f209ec50e
```

## 使用前提

1. 备忘录后端服务已启动：
   ```bash
   cd /Users/pea/Desktop/helloworld/DigitalEmployeeMemo
   python app.py
   ```

2. 服务地址：`http://localhost:5001`

## 技术实现

- 使用 curl 调用 REST API
- 支持中文账户名和内容
- 数据实时存储到 xlsx 文件
