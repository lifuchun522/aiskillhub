import { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  ChevronDown, ChevronRight, LogOut, PanelLeftClose, PanelRightClose, Sparkles, User,
} from 'lucide-react'
import { useAuth } from '../stores/userStore'
import { MenuIcon } from '../utils/icons'
import type { MenuItem } from '../api/auth'

export default function AdminLayout() {
  const { user, menus, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [collapsedGroups, setCollapsedGroups] = useState<Set<number>>(new Set())
  const [tabs, setTabs] = useState<{ path: string; title: string }[]>(() => {
    const t = findTabByPath(menus, location.pathname)
    return t ? [t] : []
  })

  const activePath = location.pathname

  const toggleGroup = (id: number) => {
    const next = new Set(collapsedGroups)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setCollapsedGroups(next)
  }

  const openTab = (path: string, title: string) => {
    navigate(path)
    setTabs((prev) => (prev.some((t) => t.path === path) ? prev : [...prev, { path, title }]))
  }

  const closeTab = (path: string) => {
    const idx = tabs.findIndex((t) => t.path === path)
    const next = tabs.filter((t) => t.path !== path)
    setTabs(next)
    if (activePath === path) {
      const target = next[idx] || next[idx - 1]
      navigate(target ? target.path : '/')
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 顶栏 */}
      <div className="app-header">
        <div className="header-left">
          <button className="header-icon" onClick={() => setSidebarCollapsed((v) => !v)}>
            <PanelLeftClose size={18} />
          </button>
          <span className="header-title">客户管理技术底座</span>
        </div>
        <div className="header-right">
          <span className="user-name">
            <User size={16} />
            {user?.real_name || user?.username}
          </span>
          <span className="divider" />
          <button className="header-icon" onClick={() => setChatCollapsed((v) => !v)}>
            <PanelRightClose size={18} />
          </button>
          <button className="header-icon" onClick={handleLogout} title="退出登录">
            <LogOut size={18} />
          </button>
        </div>
      </div>

      <div className="app-body">
        {/* 左侧菜单 */}
        <aside className={`app-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
          {menus.map((group) => (
            <div className="menu-group" key={group.id}>
              <div className="menu-group-title" onClick={() => toggleGroup(group.id)}>
                <MenuIcon name={group.icon} size={18} />
                <span>{group.name}</span>
                <span className="chevron">
                  {collapsedGroups.has(group.id) ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                </span>
              </div>
              {!collapsedGroups.has(group.id) &&
                (group.children || []).map((child) => (
                  <div
                    key={child.id}
                    className={`menu-item ${activePath === child.path ? 'active' : ''}`}
                    onClick={() => child.path && openTab(child.path, child.name)}
                  >
                    <MenuIcon name={child.icon} size={16} />
                    <span>{child.name}</span>
                  </div>
                ))}
            </div>
          ))}
        </aside>

        {/* 中间工作区 */}
        <main className="app-main">
          <div className="tabs-bar">
            {tabs.map((tab) => (
              <div key={tab.path} className={`tab ${activePath === tab.path ? 'active' : ''}`}>
                <span onClick={() => navigate(tab.path)}>{tab.title}</span>
                <span className="tab-close" onClick={() => closeTab(tab.path)}>
                  ×
                </span>
              </div>
            ))}
          </div>
          <div className="app-content">
            <Outlet />
          </div>
        </main>

        {/* 右侧 AI 对话（本期不实现） */}
        <aside className={`app-chat ${chatCollapsed ? 'collapsed' : ''}`}>
          <div className="chat-header">
            <div className="chat-logo">
              <Sparkles size={16} />
            </div>
            <span className="chat-title">AI 智能助理</span>
          </div>
          <div className="chat-body">
            <div>
              <p>AI 对话能力暂未开放</p>
              <p className="text-secondary" style={{ marginTop: 8 }}>
                后续将支持业务问答、功能导航与动态查询
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function findTabByPath(menus: MenuItem[], path: string): { path: string; title: string } | null {
  for (const g of menus) {
    for (const c of g.children || []) {
      if (c.path === path) return { path: c.path!, title: c.name }
    }
  }
  return null
}
