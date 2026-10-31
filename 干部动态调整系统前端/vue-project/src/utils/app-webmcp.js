import { nextTick } from 'vue'
import { getActivePageTools, invokeActivePageTool } from './webmcp'

const toPage = (route) => ({
  name: String(route.name),
  path: route.path,
  title: route.meta?.title || String(route.name),
  parameters: [...route.path.matchAll(/:([A-Za-z0-9_]+)/g)].map(([, parameter]) => parameter),
})

const getPages = (router) => router.getRoutes()
  .filter((route) => route.name && route.components?.default)
  .map(toPage)
  .sort((left, right) => left.path.localeCompare(right.path))

const validateNavigationInput = (input, router) => {
  if (!input || typeof input !== 'object' || Array.isArray(input) || typeof input.routeName !== 'string') {
    throw new Error('routeName 必须是页面名称')
  }

  const route = router.getRoutes().find((candidate) => String(candidate.name) === input.routeName && candidate.components?.default)
  if (!route) throw new Error(`未找到页面：${input.routeName}`)

  const parameters = toPage(route).parameters
  const supplied = input.params === undefined ? {} : input.params
  if (!supplied || typeof supplied !== 'object' || Array.isArray(supplied)) {
    throw new Error('params 必须是对象')
  }

  const unexpected = Object.keys(supplied).filter((key) => !parameters.includes(key))
  if (unexpected.length) throw new Error(`不支持的页面参数：${unexpected.join('、')}`)

  const params = {}
  for (const parameter of parameters) {
    const value = supplied[parameter]
    if ((typeof value !== 'string' && typeof value !== 'number') || String(value).trim() === '') {
      throw new Error(`页面参数 ${parameter} 必须是非空字符串或数字`)
    }
    params[parameter] = String(value)
  }

  return { name: route.name, params }
}

export function registerApplicationWebMcpTools(router) {
  const context = typeof document === 'undefined' ? undefined : document.modelContext
  if (!context?.registerTool) return () => {}

  const lifecycle = new AbortController()
  const tools = [
    {
      name: 'list_openhrm_pages',
      title: '列出 OpenHRM 页面',
      description: '列出当前前端已注册的所有可导航页面及其必需路由参数。用于选择后续要访问的页面。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute() {
        return { pages: getPages(router) }
      },
    },
    {
      name: 'navigate_openhrm_page',
      title: '打开 OpenHRM 页面',
      description: '导航至一个已注册的 OpenHRM 页面。详情页面必须同时提供该页面要求的路由参数；此操作只改变当前界面，不会保存业务数据。',
      inputSchema: {
        type: 'object',
        properties: {
          routeName: { type: 'string', description: '由 list_openhrm_pages 返回的页面名称。' },
          params: {
            type: 'object',
            additionalProperties: { type: ['string', 'number'] },
            description: '目标页面路径中声明的参数，例如 {"id": 12}。',
          },
        },
        required: ['routeName'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      async execute(input) {
        const target = validateNavigationInput(input, router)
        await router.push(target)
        await nextTick()
        return { page: toPage(router.currentRoute.value) }
      },
    },
    {
      name: 'read_openhrm_current_page',
      title: '读取当前 OpenHRM 页面',
      description: '返回当前页面的路由名称、路径、标题和所需路由参数，用于确认导航已经完成。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute() {
        return { page: toPage(router.currentRoute.value) }
      },
    },
    {
      name: 'list_openhrm_current_page_actions',
      title: '列出当前页面操作',
      description: '列出当前 OpenHRM 页面通过 invoke_openhrm_page_action 可执行的读取、暂存和完成操作，以及各自的输入约束。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute() {
        return { page: toPage(router.currentRoute.value), actions: getActivePageTools() }
      },
    },
    {
      name: 'invoke_openhrm_page_action',
      title: '执行当前页面操作',
      description: '执行 list_openhrm_current_page_actions 所列的一个当前页面操作。名称中 start、stage、preview 表示不保存或预览；complete 表示会产生相应的业务写入。',
      inputSchema: {
        type: 'object',
        properties: {
          action: { type: 'string', description: '由 list_openhrm_current_page_actions 返回的操作名称。' },
          input: { type: 'object', description: '符合该操作 inputSchema 的输入对象。' },
        },
        required: ['action', 'input'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) {
        if (!input || typeof input !== 'object' || Array.isArray(input) || typeof input.action !== 'string' || !input.input || typeof input.input !== 'object' || Array.isArray(input.input)) {
          throw new Error('action 必须是字符串，input 必须是对象')
        }
        return { action: input.action, result: await invokeActivePageTool(input.action, input.input) }
      },
    },
  ]

  tools.forEach((tool) => {
    try {
      void Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch((error) => {
        console.error(`WebMCP tool registration failed: ${tool.name}`, error)
      })
    } catch (error) {
      console.error(`WebMCP tool registration failed: ${tool.name}`, error)
    }
  })

  return () => lifecycle.abort()
}
