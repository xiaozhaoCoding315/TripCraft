import type { ReactNode } from 'react'
import type { TravelPlan } from '../types/travel'

/** 插件可以注册到的插槽 */
export type PluginSlot = 'sidebar' | 'toolbar' | 'context-panel' | 'dashboard-tab'

/** 插件元信息 */
export interface PluginMeta {
  id: string
  name: string
  version: string
  description: string
  icon?: string
  slot: PluginSlot
}

/** 插件渲染上下文 */
export interface PluginContext {
  plan?: TravelPlan
  userId?: string
}

/** 插件接口 */
export interface TripCraftPlugin {
  meta: PluginMeta
  /** 渲染插件UI */
  render: (ctx: PluginContext) => ReactNode
  /** 可选：插件加载时的初始化 */
  onInit?: () => void | Promise<void>
  /** 可选：插件卸载时的清理 */
  onDestroy?: () => void
}
