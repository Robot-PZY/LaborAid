import Settings, { type SettingsTab } from '../Settings';

const SECTIONS: Record<
  string,
  { tabs: SettingsTab[]; initialTab: SettingsTab; title: string; subtitle: string }
> = {
  models: {
    tabs: ['llm'],
    initialTab: 'llm',
    title: '模型配置',
    subtitle: '配置平台统一的文本模型与视觉/OCR 模型，所有用户共用',
  },
  apis: {
    tabs: ['external'],
    initialTab: 'external',
    title: '接口管理',
    subtitle: '新增或维护外部法规、案例等 API 数据源',
  },
  system: {
    tabs: ['vector', 'general'],
    initialTab: 'vector',
    title: '系统参数',
    subtitle: '向量数据库与通用运行参数',
  },
};

interface AdminConfigProps {
  section: keyof typeof SECTIONS;
}

export default function AdminConfig({ section }: AdminConfigProps) {
  const cfg = SECTIONS[section] ?? SECTIONS.models;
  return (
    <Settings
      initialTab={cfg.initialTab}
      visibleTabs={cfg.tabs}
      title={cfg.title}
      subtitle={cfg.subtitle}
    />
  );
}
