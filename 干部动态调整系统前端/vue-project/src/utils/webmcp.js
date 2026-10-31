let activePageTools = new Map()
let activeRegistration = null

const toSerializable = value => value === undefined ? null : JSON.parse(JSON.stringify(value))

// WebMCP binds tools to a document, rather than to a Vue component. In a SPA,
// registering a new set on every route visit eventually exhausts the browser's
// per-document tool limit even when AbortController cleanup is used. Components
// therefore publish their actions here; app-webmcp exposes a stable dispatcher.
export function registerModelContextTools(tools) {
  const registration = Symbol('openhrm-page-tools')
  activeRegistration = registration
  activePageTools = new Map(tools.map(tool => [tool.name, tool]))

  return () => {
    if (activeRegistration === registration) {
      activeRegistration = null
      activePageTools = new Map()
    }
  }
}

export function getActivePageTools() {
  return [...activePageTools.values()].map(({ name, title, description, inputSchema, annotations }) => ({ name, title, description, inputSchema, annotations }))
}

export async function invokeActivePageTool(name, input) {
  const tool = activePageTools.get(name)
  if (!tool) throw new Error(`当前页面不支持操作：${name}`)
  return toSerializable(await tool.execute(input))
}
