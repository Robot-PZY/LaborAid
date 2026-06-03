import type { LucideIcon } from 'lucide-react';
import {
  LayoutGrid,
  FileText,
  Search,
  ShieldCheck,
  Upload,
  BookOpen,
  Calculator,
  Library,
  Briefcase,
  Building2,
  FileCode,
  Settings,
  Compass,
  History,
  HeartHandshake,
  Archive,
} from 'lucide-react';
import { migrateRecentAgentsKey } from '@/lib/storage-keys';

/** 导航与工具注册（每项 = 一个可独立调用的功能页面）。协作智能体按阶段分组，见 backend capabilities.py。 */

export type AgentCategory =
  | 'hub'
  | 'service'
  | 'core'
  | 'special'
  | 'other'
  | 'management'
  | 'system';

export interface AgentConfig {
  id: string;
  name: string;
  shortName: string;
  description: string;
  icon: LucideIcon;
  route: string;
  color: string;
  bgColor: string;
  category: AgentCategory;
  enabled: boolean;
  showInNav?: boolean;
  showInHub?: boolean;
}

export const AGENT_CATEGORIES: Record<
  Exclude<AgentCategory, 'hub' | 'system'>,
  string
> = {
  service: '维权服务',
  management: '案件管理',
  core: '维权工具',
  special: '专项入口',
  other: '其他功能',
};

export const AGENTS: AgentConfig[] = [
  {
    id: 'hub',
    name: '服务首页',
    shortName: '首页',
    description: '维权入口、官方服务链接与常用工具',
    icon: LayoutGrid,
    route: '/',
    color: 'text-foreground',
    bgColor: 'bg-ink',
    category: 'hub',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
  {
    id: 'guidance',
    name: '办事资源',
    shortName: '资源',
    description: '申诉网站、热线电话与属地官方办事入口',
    icon: Compass,
    route: '/guidance',
    color: 'text-rose-600',
    bgColor: 'bg-rose-500',
    category: 'service',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
  {
    id: 'records',
    name: '我的记录',
    shortName: '记录',
    description: '查看案件、文书、证据与研究等个人维权记录',
    icon: History,
    route: '/records',
    color: 'text-sky-600',
    bgColor: 'bg-sky-500',
    category: 'service',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
  {
    id: 'channels',
    name: '专项维权',
    shortName: '专项',
    description: '已并入首页专项通道入口',
    icon: HeartHandshake,
    route: '/?intake=special#intake-desk',
    color: 'text-amber-700',
    bgColor: 'bg-amber-600',
    category: 'special',
    enabled: true,
    showInNav: false,
    showInHub: false,
  },
  {
    id: 'vault',
    name: '我的材料',
    shortName: '材料',
    description: '维权材料按账号长期保存，跨月可随时下载',
    icon: Archive,
    route: '/vault',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-600',
    category: 'service',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
  {
    id: 'docgen',
    name: '生成文书',
    shortName: '文书',
    description: 'AI 起草起诉状、答辩状、仲裁申请书等法律文书，支持一键导出 Word',
    icon: FileText,
    route: '/documents',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-500',
    category: 'core',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'contract',
    name: '审查合同',
    shortName: '合同',
    description: '识别劳动合同等风险条款，给出合规审查意见与修改建议',
    icon: ShieldCheck,
    route: '/contracts',
    color: 'text-orange-600',
    bgColor: 'bg-orange-500',
    category: 'core',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'evidence',
    name: '整理证据',
    shortName: '证据',
    description: '上传证据材料，自动 OCR 识别文字，AI 分析并整理证据清单',
    icon: Upload,
    route: '/evidence',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-500',
    category: 'core',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'search',
    name: '检索法规',
    shortName: '法规',
    description: '跨法规、案例、知识库的智能混合检索与 AI 摘要',
    icon: Search,
    route: '/search',
    color: 'text-violet-600',
    bgColor: 'bg-violet-500',
    category: 'other',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'enterprise',
    name: '查询企业',
    shortName: '企业',
    description: '查询用人单位工商登记与公开风险记录，核实企业主体与信用状况',
    icon: Building2,
    route: '/enterprise',
    color: 'text-teal-600',
    bgColor: 'bg-teal-500',
    category: 'other',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'limitation_calc',
    name: '时效/期限计算',
    shortName: '时效',
    description: '根据事件时间与是否在职，提示仲裁时效与关键截止日期',
    icon: Calculator,
    route: '/tools/limitation',
    color: 'text-slate-700',
    bgColor: 'bg-slate-600',
    category: 'other',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
  {
    id: 'compensation_calc',
    name: '赔偿/补偿计算',
    shortName: '补偿',
    description: '按月工资、工龄与解除类型，粗算经济补偿/赔偿金区间并给出公式',
    icon: Calculator,
    route: '/tools/compensation',
    color: 'text-slate-700',
    bgColor: 'bg-slate-600',
    category: 'other',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
  {
    id: 'research',
    name: '分析案情',
    shortName: '案情',
    description: '汇总案件、证据与文书等已有材料，生成维权阶段总结报告',
    icon: BookOpen,
    route: '/research',
    color: 'text-pink-600',
    bgColor: 'bg-pink-500',
    category: 'core',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'knowledge',
    name: '法律知识库',
    shortName: '法规',
    description: '平台法律知识库，供检索法规与分析案情时引用',
    icon: Library,
    route: '/admin/knowledge',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-500',
    category: 'other',
    enabled: false,
    showInNav: false,
    showInHub: false,
  },
  {
    id: 'cases',
    name: '管理案件',
    shortName: '案件',
    description: '先建立案件档案，再关联文书、证据与研究资料',
    icon: Briefcase,
    route: '/cases',
    color: 'text-blue-600',
    bgColor: 'bg-blue-500',
    category: 'management',
    enabled: true,
    showInNav: true,
    showInHub: true,
  },
  {
    id: 'templates',
    name: '文书模板',
    shortName: '模板',
    description: '法律文书模板管理，支持自定义结构与变量',
    icon: FileCode,
    route: '/templates',
    color: 'text-amber-600',
    bgColor: 'bg-amber-500',
    category: 'management',
    enabled: true,
    showInNav: false,
    showInHub: false,
  },
  {
    id: 'settings',
    name: '个人设置',
    shortName: '设置',
    description: '账号信息与偏好',
    icon: Settings,
    route: '/settings',
    color: 'text-slate-600',
    bgColor: 'bg-slate-500',
    category: 'system',
    enabled: true,
    showInNav: true,
    showInHub: false,
  },
];

const RECENT_KEY = 'laboraid_recent_agents';

export function getNavAgents(): AgentConfig[] {
  return AGENTS.filter((a) => a.showInNav && a.enabled);
}

export function getHubAgents(): AgentConfig[] {
  return AGENTS.filter((a) => a.showInHub && a.enabled);
}

/** 按 id 取已启用智能体（不受 showInHub 限制，供首页等自定义编排） */
export function getAgentsByIds(ids: readonly string[]): AgentConfig[] {
  return ids
    .map((id) => AGENTS.find((a) => a.id === id && a.enabled))
    .filter(Boolean) as AgentConfig[];
}

export function getAgentByRoute(route: string): AgentConfig | undefined {
  if (route === '/') return AGENTS.find((a) => a.id === 'hub');
  return AGENTS.find((a) => a.route === route);
}

export function getAgentsByCategory(category: AgentCategory): AgentConfig[] {
  return AGENTS.filter((a) => a.category === category && a.enabled && a.showInHub);
}

export function recordAgentVisit(agentId: string): void {
  try {
    const recent: string[] = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    const next = [agentId, ...recent.filter((id) => id !== agentId)].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export function getRecentAgentIds(): string[] {
  migrateRecentAgentsKey();
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
  } catch {
    return [];
  }
}

export function getRouteLabelMap(): Record<string, string> {
  const map: Record<string, string> = {};
  AGENTS.forEach((a) => {
    map[a.route] = a.id === 'hub' ? '服务首页' : a.name;
  });
  map['/guidance'] = '办事资源';
  return map;
}

/** 不在智能体页头展示的路由（服务页与个人设置） */
export const ROUTES_WITHOUT_AGENT_HEADER = new Set([
  '/',
  '/settings',
  '/guidance',
  '/records',
  '/channels',
  '/vault',
]);
