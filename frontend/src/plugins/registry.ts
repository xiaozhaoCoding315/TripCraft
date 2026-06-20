import type { TripCraftPlugin, PluginSlot, PluginContext } from './types'

/** 插件注册中心 — 单例模式管理所有已注册插件 */
class PluginRegistry {
  private plugins: Map<string, TripCraftPlugin> = new Map()

  /** 注册一个插件 */
  register(plugin: TripCraftPlugin): void {
    if (this.plugins.has(plugin.meta.id)) {
      console.warn(`[PluginRegistry] Plugin "${plugin.meta.id}" already registered, overwriting.`)
    }
    this.plugins.set(plugin.meta.id, plugin)
    console.log(`[PluginRegistry] Registered: ${plugin.meta.name} v${plugin.meta.version}`)
  }

  /** 批量注册 */
  registerAll(plugins: TripCraftPlugin[]): void {
    plugins.forEach(p => this.register(p))
  }

  /** 注销插件 */
  unregister(pluginId: string): void {
    const plugin = this.plugins.get(pluginId)
    if (plugin?.onDestroy) {
      plugin.onDestroy()
    }
    this.plugins.delete(pluginId)
  }

  /** 获取某个插槽的所有插件 */
  getBySlot(slot: PluginSlot): TripCraftPlugin[] {
    return Array.from(this.plugins.values()).filter(p => p.meta.slot === slot)
  }

  /** 渲染某个插槽的所有插件 */
  renderSlot(slot: PluginSlot, ctx: PluginContext = {}): React.ReactNode[] {
    return this.getBySlot(slot).map(plugin => plugin.render(ctx))
  }

  /** 获取所有已注册插件 */
  list(): TripCraftPlugin[] {
    return Array.from(this.plugins.values())
  }

  /** 初始化所有插件 */
  async initAll(): Promise<void> {
    for (const plugin of this.plugins.values()) {
      if (plugin.onInit) {
        try {
          await plugin.onInit()
        } catch (e) {
          console.warn(`[PluginRegistry] Init failed for ${plugin.meta.id}:`, e)
        }
      }
    }
  }
}

/** 全局单例 */
export const pluginRegistry = new PluginRegistry()
