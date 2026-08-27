import request from '@/utils/request'

export const getRoles = () => request.get('/admin/roles/')
export const getRole = (id) => request.get(`/admin/roles/${id}/`)
export const createRole = (data) => request.post('/admin/roles/', data)
export const updateRole = (id, data) => request.patch(`/admin/roles/${id}/`, data)
export const deleteRole = (id) => request.delete(`/admin/roles/${id}/`)
export const updateRolePermissions = (id, permissions) => request.put(`/admin/roles/${id}/permissions/`, { permissions })
export const getPermissionCatalog = () => request.get('/admin/permissions/catalog/')
export const getAdminUsers = (params) => request.get('/admin/users/', { params })
export const getUserRoles = (userId) => request.get(`/admin/users/${userId}/roles/`)
export const assignUserRoles = (userId, roleIds) => request.put(`/admin/users/${userId}/roles/assign/`, { role_ids: roleIds })
