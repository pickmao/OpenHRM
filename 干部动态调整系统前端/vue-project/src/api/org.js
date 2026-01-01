import request from '@/utils/request'

/**
 * 组织架构管理 API
 */

// ==================== 部门管理 ====================

/**
 * 获取组织树
 * @returns {Promise}
 */
export function getOrgTree() {
  return request({
    url: '/org/units/tree/',
    method: 'get'
  })
}

/**
 * 获取部门列表
 * @param {Object} params - 查询参数
 * @param {string} params.search - 搜索关键词
 * @param {string} params.unit_type - 部门类型
 * @param {boolean} params.is_active - 是否启用
 * @param {boolean} params.root_only - 只获取根节点
 * @returns {Promise}
 */
export function getDepartmentList(params) {
  return request({
    url: '/org/units/',
    method: 'get',
    params
  })
}

/**
 * 获取部门详情
 * @param {string} id - 部门ID
 * @returns {Promise}
 */
export function getDepartmentDetail(id) {
  return request({
    url: `/org/units/${id}`,
    method: 'get'
  })
}

/**
 * 新增部门
 * @param {Object} data
 * @param {string} data.name - 部门名称
 * @param {string} data.code - 部门编码
 * @param {string} data.unit_type - 部门类型
 * @param {string} data.parent - 父部门ID
 * @param {number} data.sort_order - 排序
 * @param {boolean} data.is_active - 是否启用
 * @returns {Promise}
 */
export function createDepartment(data) {
  return request({
    url: '/org/units/',
    method: 'post',
    data
  })
}

/**
 * 更新部门
 * @param {string} id - 部门ID
 * @param {Object} data
 * @returns {Promise}
 */
export function updateDepartment(id, data) {
  return request({
    url: `/org/units/${id}`,
    method: 'patch',
    data
  })
}

/**
 * 删除部门
 * @param {string} id - 部门ID
 * @returns {Promise}
 */
export function deleteDepartment(id) {
  return request({
    url: `/org/units/${id}`,
    method: 'delete'
  })
}

/**
 * 移动部门
 * @param {string} id - 部门ID
 * @param {Object} data
 * @param {string} data.new_parent_id - 新父部门ID
 * @param {number} data.position - 排序位置
 * @returns {Promise}
 */
export function moveDepartment(id, data) {
  return request({
    url: `/org/units/${id}/move/`,
    method: 'post',
    data
  })
}

/**
 * 部门排序
 * @param {Object} data
 * @param {string} data.parent_id - 父部门ID
 * @param {Array<string>} data.ordered_ids - 排序后的部门ID列表
 * @returns {Promise}
 */
export function reorderDepartments(data) {
  return request({
    url: '/org/units/reorder/',
    method: 'post',
    data
  })
}

// ==================== 部门成员管理 ====================

/**
 * 获取部门成员列表
 * @param {string} unitId - 部门ID
 * @param {Object} params - 查询参数
 * @param {boolean} params.include_children - 是否包含子部门成员
 * @param {string} params.search - 搜索关键词
 * @param {boolean} params.primary_only - 只获取主部门成员
 * @returns {Promise}
 */
export function getDepartmentMembers(unitId, params) {
  return request({
    url: `/org/units/${unitId}/members`,
    method: 'get',
    params
  })
}

/**
 * 设置部门负责人
 * @param {string} unitId - 部门ID
 * @param {Object} data
 * @param {string} data.user_id - 用户ID
 * @returns {Promise}
 */
export function setDepartmentManager(unitId, data) {
  return request({
    url: `/org/units/${unitId}/manager/`,
    method: 'post',
    data
  })
}

/**
 * 添加成员到部门
 * @param {Object} data
 * @param {string} data.user - 用户ID
 * @param {string} data.unit - 部门ID
 * @param {boolean} data.is_primary - 是否主部门
 * @param {string} data.position - 职务
 * @param {boolean} data.is_manager - 是否负责人
 * @param {string} data.effective_from - 生效日期
 * @param {string} data.effective_to - 失效日期
 * @returns {Promise}
 */
export function addMember(data) {
  return request({
    url: '/org/memberships/',
    method: 'post',
    data
  })
}

/**
 * 移除部门成员
 * @param {string} id - 成员关系ID
 * @returns {Promise}
 */
export function removeMember(id) {
  return request({
    url: `/org/memberships/${id}`,
    method: 'delete'
  })
}

/**
 * 查询用户的组织归属
 * @param {string} userId - 用户ID
 * @returns {Promise}
 */
export function getUserMemberships(userId) {
  return request({
    url: '/org/memberships/by_user/',
    method: 'get',
    params: { user_id: userId }
  })
}

/**
 * 获取成员详情
 * @param {string} id - 成员关系ID
 * @returns {Promise}
 */
export function getMemberDetail(id) {
  return request({
    url: `/org/memberships/${id}`,
    method: 'get'
  })
}

/**
 * 更新成员信息
 * @param {string} id - 成员关系ID
 * @param {Object} data
 * @returns {Promise}
 */
export function updateMember(id, data) {
  return request({
    url: `/org/memberships/${id}`,
    method: 'patch',
    data
  })
}
