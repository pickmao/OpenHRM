通常“组织架构”在 Django 里做成一组 REST 接口，核心取决于你是否要同时覆盖：**部门树（Organization Unit）**、**人员归属（Membership）**、**岗位/职务（Position）**、以及**权限（RBAC）**。

下面给你一个可落地的接口拆分方式：先给“最小可用集”，再给“企业常见增强集”。你可以按业务复杂度选用。

---

## 最小可用：8–10 个接口就能跑起来（部门树 + 人员归属）

### A. 部门（组织单元）OrgUnit

1. **获取组织树**

   * `GET /api/org/units/tree`
   * 返回整棵树（或按 scope/tenant 过滤）
2. **获取部门详情**

   * `GET /api/org/units/{id}`
3. **新增部门**

   * `POST /api/org/units`
4. **更新部门**

   * `PATCH /api/org/units/{id}`
5. **删除部门**

   * `DELETE /api/org/units/{id}`
   * 建议约束：有子部门/有人挂靠时禁止删除或提供级联策略

> 备注：如果你不需要单独的 “tree” 接口，也可以用 `GET /api/org/units?tree=1` 合并掉一个。

### B. 部门成员（人员归属）

6. **列出部门成员**

   * `GET /api/org/units/{id}/members`
   * 支持分页、搜索、仅直属/含子部门等参数

7. **添加成员到部门**

   * `POST /api/org/units/{id}/members`
   * body：`{ "user_id": "...", "is_primary": true/false, "title": "...", "effective_from": "...", ... }`

8. **移除成员**

   * `DELETE /api/org/memberships/{membership_id}`（推荐）
   * 或 `DELETE /api/org/units/{id}/members/{user_id}`（简单但不利于多归属）

9. **查询某个用户的组织归属**

   * `GET /api/org/users/{user_id}/memberships`
   * 用于“个人所属部门/主部门/兼职部门”展示与权限计算

这套通常就足够支撑：组织树展示、部门 CRUD、部门人员管理、按人查归属。

---

## 企业常见增强：再加 6–10 个接口（移动排序、岗位、负责人、历史）

### C. 树结构调整（非常常见）

10. **移动部门（换父节点/调整顺序）**

* `POST /api/org/units/{id}/move`
* body：`{ "new_parent_id": "...", "position": 3 }`

11. **部门排序**

* `POST /api/org/units/reorder`
* body：`{ "parent_id": "...", "ordered_ids": [...] }`

> 如果你用 MPTT / Treebeard，移动与排序是高频需求，单独接口比 PATCH parent_id 更安全（可加事务、校验环）。

### D. 负责人/汇报线（如果你要“部门负责人”或“上下级”）

12. **设置/变更部门负责人**

* `POST /api/org/units/{id}/manager`
* body：`{ "user_id": "..." }`

13. **查询用户汇报链/下属**

* `GET /api/org/users/{user_id}/reporting-line`
* `GET /api/org/users/{user_id}/subordinates`

### E. 岗位/职务（可选，但很多组织管理会要）

14. **岗位 CRUD**

* `GET/POST /api/org/positions`
* `PATCH/DELETE /api/org/positions/{id}`

15. **成员岗位任命**

* `POST /api/org/memberships/{membership_id}/assign-position`

### F. 历史与审计（想做规范管理时）

16. **成员调动记录**

* `GET /api/org/transfers?user_id=&from=&to=`

17. **组织变更审计**

* `GET /api/org/audits?unit_id=&actor_id=&from=&to=`

---

## 一句话建议：你到底“该设计几个”？

* **只做组织树 + 部门人员管理：8–10 个接口**（上面的最小可用）
* **要支持拖拽移动/排序 + 负责人：12–13 个接口**
* **再加岗位与历史审计：16–20 个接口**

---

## 设计要点（避免后期返工）

* **成员关系建议用“Membership”建模**（user_id + unit_id + is_primary + title/position + effective dates），这样天然支持一人多部门、调岗历史。
* **树查询要支持“含子部门”**（部门成员列表、统计类接口都很常用）。
* **删除策略要明确**：禁止删除含子节点/含成员，或提供“转移到其他部门”的流程接口。

如果你告诉我你需要的范围（是否一人多部门、是否要拖拽排序、是否要负责人/汇报线、是否要岗位与历史），我可以直接给你一份更贴近你场景的 **接口清单 + 请求/响应字段规范**（甚至连 DRF ViewSet/Serializer 的结构也能给到）。
