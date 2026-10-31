import fs from 'node:fs/promises'
import path from 'node:path'
import { gzipSync } from 'node:zlib'
import assert from 'node:assert/strict'

const root = path.resolve('dist')
const manifest = JSON.parse(await fs.readFile(path.join(root, '.vite/manifest.json'), 'utf8'))
const keys = ['index.html', 'src/views/Login.vue']
const files = new Set()
const visited = new Set()
function visit(key) {
  if (visited.has(key)) return
  visited.add(key)
  const chunk = manifest[key]
  assert(chunk, `Missing initial-route chunk: ${key}`)
  files.add(chunk.file)
  for (const css of chunk.css || []) files.add(css)
  for (const dependency of chunk.imports || []) visit(dependency)
}
keys.forEach(visit)
let raw = 0, gzip = 0, cssBytes = 0
for (const file of files) {
  const content = await fs.readFile(path.join(root, file))
  raw += content.length
  gzip += gzipSync(content).length
  if (file.endsWith('.css')) cssBytes += content.length
}
const entry = await fs.stat(path.join(root, manifest['index.html'].file))
console.log(JSON.stringify({ entryBytes: entry.size, loginRawBytes: raw, loginGzipBytes: gzip, loginCssBytes: cssBytes, files: files.size }, null, 2))
assert(entry.size < 300_000, 'Entry exceeds 300 KB; check for full component-library imports')
assert(gzip < 160_000, 'Login initial resources exceed the 160 KB gzip budget')
assert(cssBytes < 100_000, 'Login CSS exceeds 100 KB; check for full library styles')
