import test from 'node:test'
import assert from 'node:assert/strict'
import { firstApiError } from './apiError.js'

test('preserves the complete no-recipient response from campaign creation', () => {
  const error = '当前勾选的表单没有匹配到填报人。请调整范围或手动指定。'
  assert.equal(firstApiError({ recipients: error }), error)
})

test('handles field arrays and nested serializer validation errors', () => {
  assert.equal(firstApiError({ deadline_at: ['截止时间必须晚于当前时间。'] }), '截止时间必须晚于当前时间。')
  assert.equal(firstApiError({ recipients: [{ user_id: ['用户不存在。'] }] }), '用户不存在。')
})

test('gives a detail message priority and accepts top-level lists and strings', () => {
  assert.equal(firstApiError({ other: ['其他错误'], detail: '没有权限。' }), '没有权限。')
  assert.equal(firstApiError(['请填写批次名称。']), '请填写批次名称。')
  assert.equal(firstApiError('服务暂不可用。'), '服务暂不可用。')
})

test('skips empty entries and returns an empty string for missing error data', () => {
  assert.equal(firstApiError({ unused: [], recipients: ['', '无可用填报人。'] }), '无可用填报人。')
  for (const value of [undefined, null, {}, [], '', false, 500]) assert.equal(firstApiError(value), '')
})
