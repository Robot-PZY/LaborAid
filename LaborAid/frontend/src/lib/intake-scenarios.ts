import intakeScenarios from '@/config/labor/intake-scenarios.json';
import { getChannel, listChannels, type ChannelConfig, type ChannelScenario } from '@/lib/channels';

export type IntakeFormFieldType = 'text' | 'textarea' | 'select' | 'number';

export type IntakeFormField = {
  id: string;
  label: string;
  type?: IntakeFormFieldType;
  required?: boolean;
  placeholder?: string;
  options?: string[];
  maxLength?: number;
};

type ScenarioMeta = {
  cause_type?: string;
  form_fields?: IntakeFormField[];
};

type IntakeScenariosConfig = {
  channels?: Record<string, { common_fields?: IntakeFormField[] }>;
  scenarios?: Record<string, ScenarioMeta>;
};

const cfg = intakeScenarios as IntakeScenariosConfig;

export function scenarioKey(channelId: string, scenarioId: string): string {
  return `${channelId}:${scenarioId}`;
}

export function getChannelCommonFields(channelId: string): IntakeFormField[] {
  return cfg.channels?.[channelId]?.common_fields ?? [];
}

export function getScenarioFormFields(channelId: string, scenarioId: string): IntakeFormField[] {
  const meta = cfg.scenarios?.[scenarioKey(channelId, scenarioId)];
  return [
    ...getChannelCommonFields(channelId),
    ...(meta?.form_fields ?? []),
  ];
}

export function getScenarioCauseType(channelId: string, scenarioId: string): string | undefined {
  return cfg.scenarios?.[scenarioKey(channelId, scenarioId)]?.cause_type;
}

/** 可填表的场景：配置中有 form_fields 且非 quick_action 类场景 */
export function listIntakeScenarios(channel: ChannelConfig): ChannelScenario[] {
  const scenarios = channel.scenarios ?? [];
  return scenarios.filter((s) => {
    const key = scenarioKey(channel.id, s.id);
    return Boolean(cfg.scenarios?.[key]?.form_fields?.length);
  });
}

export function listIntakeChannels(): ChannelConfig[] {
  return listChannels().filter((ch) => listIntakeScenarios(ch).length > 0);
}

/** 与后端 structured_builder._render_case_facts 一致，用于恢复完整案情 */
export function renderStructuredCaseFacts(
  channelTitle: string,
  scenarioTitle: string,
  answers: Record<string, string>,
  fields: IntakeFormField[],
): string {
  const lines = [`【专项维权】${channelTitle} · ${scenarioTitle}`, ''];
  for (const field of fields) {
    const val = answers[field.id]?.trim();
    if (!val) continue;
    lines.push(`${field.label}：${val}`);
  }
  return lines.join('\n').trim();
}

export function validateFormAnswers(
  fields: IntakeFormField[],
  answers: Record<string, string>,
): string[] {
  const errors: string[] = [];
  for (const field of fields) {
    if (!field.required) continue;
    const val = answers[field.id]?.trim();
    if (!val) errors.push(`请填写${field.label}`);
  }
  return errors;
}
