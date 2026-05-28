const STORAGE_KEY = 'laboraid_channel_checklist';

type ChecklistStore = Record<string, Record<number, boolean>>;

function storeKey(channelId: string, scenarioId: string): string {
  return `${channelId}:${scenarioId}`;
}

function readAll(): ChecklistStore {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') as ChecklistStore;
  } catch {
    return {};
  }
}

function writeAll(data: ChecklistStore): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function loadScenarioChecklist(
  channelId: string,
  scenarioId: string,
): Record<number, boolean> {
  return readAll()[storeKey(channelId, scenarioId)] || {};
}

export function saveScenarioChecklist(
  channelId: string,
  scenarioId: string,
  checked: Record<number, boolean>,
): void {
  const all = readAll();
  all[storeKey(channelId, scenarioId)] = checked;
  writeAll(all);
}

export function clearScenarioChecklist(channelId: string, scenarioId: string): void {
  const all = readAll();
  delete all[storeKey(channelId, scenarioId)];
  writeAll(all);
}

export function countScenarioChecklist(
  channelId: string,
  scenarioId: string,
  total: number,
): { done: number; total: number } {
  const checked = loadScenarioChecklist(channelId, scenarioId);
  const done = Array.from({ length: total }, (_, i) => checked[i]).filter(Boolean).length;
  return { done, total };
}
