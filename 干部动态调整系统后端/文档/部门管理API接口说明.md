# 部门管理 API 接口说明

## 已实现的接口列表

### A. 部门（组织单元）管理 - `/api/org/units/`

#### 1. 获取组织树
- **接口**: `GET /api/org/units/tree/`
- **描述**: 返回完整的组织架构树
- **响应示例**:
```json
[
  {
    "id": "uuid",
    "name": "总部",
    "code": "HQ",
    "unit_type": "BRANCH",
    "label": "总部",
    "value": "uuid",
    "is_active": true,
    "sort_order": 0,
    "children": [...]
  }
]
```

#### 2. 获取部门列表
- **接口**: `GET /api/org/units/`
- **参数**:
  - `search`: 搜索名称或编码
  - `unit_type`: 部门类型（BRANCH/DEPARTMENT/TEAM等）
  - `is_active`: 是否启用（true/false）
  - `root_only`: 只获取根节点（true/false）

#### 3. 获取部门详情
- **接口**: `GET /api/org/units/{id}/`
- **响应**: 包含子部门列表、成员统计等信息

#### 4. 新增部门
- **接口**: `POST /api/org/units/`
- **请求体**:
```json
{
  "name": "技术部",
  "code": "TECH",
  "unit_type": "DEPARTMENT",
  "parent": "parent-uuid",
  "sort_order": 1,
  "is_active": true
}
```

#### 5. 更新部门
- **接口**: `PATCH /api/org/units/{id}/`
- **请求体**: 同创建

#### 6. 删除部门
- **接口**: `DELETE /api/org/units/{id}/`
- **约束**:
  - 有子部门时禁止删除
  - 有成员时禁止删除

#### 7. 移动部门（换父节点）
- **接口**: `POST /api/org/units/{id}/move/`
- **请求体**:
```json
{
  "new_parent_id": "new-parent-uuid",
  "position": 3
}
```

#### 8. 部门排序
- **接口**: `POST /api/org/units/reorder/`
- **请求体**:
```json
{
  "parent_id": "parent-uuid",
  "ordered_ids": ["id1", "id2", "id3"]
}
```

#### 9. 获取部门成员列表
- **接口**: `GET /api/org/units/{id}/members/`
- **参数**:
  - `include_children`: 是否包含子部门成员（true/false）
  - `search`: 搜索用户名/姓名/职务
  - `primary_only`: 只获取主部门成员（true/false）

#### 10. 设置部门负责人
- **接口**: `POST /api/org/units/{id}/manager/`
- **请求体**:
```json
{
  "user_id": "user-uuid"
}
```

---

### B. 部门成员管理 - `/api/org/memberships/`

#### 11. 添加成员到部门
- **接口**: `POST /api/org/memberships/`
- **请求体**:
```json
{
  "user": "user-uuid",
  "unit": "unit-uuid",
  "is_primary": true,
  "position": "技术总监",
  "is_manager": true,
  "effective_from": "2024-01-01",
  "effective_to": null
}
```

#### 12. 移除成员
- **接口**: `DELETE /api/org/memberships/{id}/`

#### 13. 查询用户的组织归属
- **接口**: `GET /api/org/memberships/by_user/?user_id={user_id}`
- **描述**: 查询某个用户所属的所有部门

#### 14. 获取成员详情
- **接口**: `GET /api/org/memberships/{id}/`

#### 15. 更新成员信息
- **接口**: `PATCH /api/org/memberships/{id}/`

---

## 数据库迁移

### 1. 生成迁移文件
```bash
cd "/mnt/d/code/干部管理系统开发/干部动态调整系统后端"
python manage.py makemigrations orgs
```

### 2. 执行迁移
```bash
python manage.py migrate orgs
```

---

## 测试接口

### 1. 创建测试部门
```bash
curl -X POST http://localhost:8000/api/org/units/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术部",
    "code": "TECH",
    "unit_type": "DEPARTMENT",
    "is_active": true
  }'
```

### 2. 获取组织树
```bash
curl -X GET http://localhost:8000/api/org/units/tree/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 添加部门成员
```bash
curl -X POST http://localhost:8000/api/org/memberships/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "USER_UUID",
    "unit": "UNIT_UUID",
    "is_primary": true,
    "position": "技术总监"
  }'
```

---

## 模型说明

### OrgUnit（组织单元）
- `id`: UUID主键
- `name`: 部门名称
- `code`: 部门编码（唯一）
- `unit_type`: 部门类型（BRANCH/DEPARTMENT/TEAM/DIVISION/OFFICE）
- `parent`: 上级部门（外键）
- `sort_order`: 排序
- `is_active`: 是否启用
- `metrics_snapshot`: 指标快照（JSON）

### Membership（部门成员）
- `id`: UUID主键
- `user`: 用户（外键）
- `unit`: 部门（外键）
- `is_primary`: 是否主部门
- `position`: 职务
- `is_manager`: 是否部门负责人
- `effective_from`: 生效日期
- `effective_to`: 失效日期
- `created_by`: 创建人

---

## API 文档访问

启动服务后，访问以下地址查看完整的 API 文档：
- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
