import {
  type ActionLogEntry,
  type AppConfig,
  type CleanupDetail,
  type ConfigFormState,
  type DashboardSnapshot,
  type DisplayState,
  type HealthState,
  KIND_LABELS,
  type ResourceAssignments,
  type ResourceEntryStatus,
  type ResourceInventoryEntry,
  type ResourceKind,
  type ResourceStatus,
  STATE_LABELS,
  TOOL_IDS,
  type ToolId,
  type SyncDetail
} from './models';

const STATE_PRIORITY: Record<DisplayState, number> = {
  conflict: 0,
  source_missing: 1,
  environment_error: 2,
  tool_unavailable: 3,
  missing: 4,
  partial: 5,
  healthy: 6,
  idle: 7
};

export interface ResourceRow {
  kind: ResourceKind;
  name: string;
  path: string;
  isDirectory: boolean;
  childrenCount: number;
  scanned: boolean;
  configuredTools: ToolId[];
  entries: ResourceEntryStatus[];
  summaryState: DisplayState;
  summaryMessage: string;
}

export interface IssueRow {
  id: string;
  kind: ResourceKind;
  name: string;
  toolId: ToolId;
  environmentId: 'windows' | 'wsl';
  state: HealthState;
  message: string;
  targetPath: string | null;
  itemCount: number;
}

function getChildrenCount(entry: ResourceInventoryEntry | undefined): number {
  if (!entry || !('children' in entry)) {
    return 0;
  }
  return Array.isArray(entry.children) ? entry.children.length : 0;
}

export function cloneAssignments(assignments: ResourceAssignments): ResourceAssignments {
  return structuredClone(assignments);
}

export function getConfigFormState(config: AppConfig): ConfigFormState {
  return {
    syncMode: config.syncMode,
    sourceDirs: structuredClone(config.sourceDirs),
    environments: structuredClone(config.environments),
    commandSubfolderSupport: structuredClone(config.commandSubfolderSupport)
  };
}

export function getConfigPatch(draft: ConfigFormState): Partial<AppConfig> {
  return {
    syncMode: draft.syncMode,
    sourceDirs: structuredClone(draft.sourceDirs),
    environments: structuredClone(draft.environments),
    commandSubfolderSupport: structuredClone(draft.commandSubfolderSupport)
  };
}

export function serialize(value: unknown): string {
  return JSON.stringify(value);
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function createLogEntry(
  label: string,
  detail: string,
  status: ActionLogEntry['status']
): ActionLogEntry {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    label,
    detail,
    status,
    time: new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  };
}

export function summarizeEntries(
  entries: ResourceEntryStatus[],
  configuredTools: ToolId[]
): Pick<ResourceRow, 'summaryState' | 'summaryMessage'> {
  if (configuredTools.length === 0) {
    return { summaryState: 'idle', summaryMessage: STATE_LABELS.idle };
  }

  if (entries.length === 0) {
    return { summaryState: 'partial', summaryMessage: '已分配但尚无状态明细' };
  }

  const ordered = [...entries].sort((left, right) => STATE_PRIORITY[left.state] - STATE_PRIORITY[right.state]);
  return {
    summaryState: ordered[0].state,
    summaryMessage: ordered[0].message || STATE_LABELS[ordered[0].state]
  };
}

export function buildResourceRows(
  kind: ResourceKind,
  inventory: ResourceInventoryEntry[],
  assignments: ResourceAssignments,
  statuses: ResourceStatus[]
): ResourceRow[] {
  const scanIndex = Object.fromEntries(inventory.map(item => [item.name, item]));
  const statusIndex = Object.fromEntries(statuses.map(item => [item.name, item]));
  const names = Array.from(
    new Set([...Object.keys(scanIndex), ...Object.keys(assignments), ...Object.keys(statusIndex)])
  ).sort((left, right) => left.localeCompare(right, 'zh-CN'));

  return names.map(name => {
    const scanned = scanIndex[name];
    const status = statusIndex[name];
    const configuredTools = assignments[name] ?? status?.configuredTools ?? [];
    const summary = summarizeEntries(status?.entries ?? [], configuredTools);

    return {
      kind,
      name,
      path: scanned?.path ?? status?.sourcePath ?? '',
      isDirectory: scanned?.isDirectory ?? status?.isDirectory ?? false,
      childrenCount: getChildrenCount(scanned),
      scanned: Boolean(scanned),
      configuredTools,
      entries: status?.entries ?? [],
      summaryState: summary.summaryState,
      summaryMessage: summary.summaryMessage
    };
  });
}

export function buildIssueRows(snapshot: DashboardSnapshot): IssueRow[] {
  const issues = [...snapshot.status.skills, ...snapshot.status.commands]
    .flatMap(resource => resource.entries.map(entry => ({ resource, entry })))
    .filter(item => item.entry.state !== 'healthy')
    .map(({ resource, entry }) => ({
      id: `${resource.kind}:${resource.name}:${entry.environmentId}:${entry.toolId}`,
      kind: resource.kind,
      name: resource.name,
      toolId: entry.toolId,
      environmentId: entry.environmentId,
      state: entry.state,
      message: entry.message,
      targetPath: entry.targetPath,
      itemCount: entry.itemCount
    }));

  return issues.sort((left, right) => {
    const delta = STATE_PRIORITY[left.state] - STATE_PRIORITY[right.state];
    if (delta !== 0) {
      return delta;
    }
    return `${left.kind}-${left.name}`.localeCompare(`${right.kind}-${right.name}`, 'zh-CN');
  });
}

export function countCleanupCandidates(issues: IssueRow[]): number {
  return issues.filter(issue => ['conflict', 'missing', 'source_missing'].includes(issue.state)).length;
}

export function countConfigured(assignments: ResourceAssignments): number {
  return Object.values(assignments).filter(tools => tools.length > 0).length;
}

export function summarizeSyncDetails(details: SyncDetail[]): string {
  const success = details.filter(item => item.success).length;
  const skipped = details.filter(item => item.skipped).length;
  const failed = details.length - success - skipped;
  return `成功 ${success} / 跳过 ${skipped} / 失败 ${failed}`;
}

export function summarizeCleanup(details: CleanupDetail[]): string {
  if (details.length === 0) {
    return '没有需要清理的目标';
  }
  const success = details.filter(item => item.success).length;
  return `已处理 ${details.length} 条，成功 ${success} 条`;
}

export function getOverviewStats(
  snapshot: DashboardSnapshot,
  issueCount: number,
  cleanupCandidateCount: number
) {
  const managedSkills = countConfigured(snapshot.config.resources.skills);
  const managedCommands = countConfigured(snapshot.config.resources.commands);
  const enabledTargets = TOOL_IDS.length + (snapshot.config.environments.wsl.enabled ? TOOL_IDS.length : 0);

  return [
    { label: '已纳管 Skills', value: managedSkills, note: `${snapshot.inventory.skills.length} 个源项` },
    { label: '已纳管 Commands', value: managedCommands, note: `${snapshot.inventory.commands.length} 个源项` },
    { label: '目标通道', value: enabledTargets, note: snapshot.config.syncMode === 'copy' ? '复制模式' : '符号链接模式' },
    { label: '异常条目', value: issueCount, note: `${cleanupCandidateCount} 条可清理` }
  ];
}

export function formatKindName(kind: ResourceKind, name: string): string {
  return `${KIND_LABELS[kind]} / ${name}`;
}

export async function fetchDashboardSnapshot(): Promise<DashboardSnapshot> {
  const [config, status, wslRuntime, skills, commands] = await Promise.all([
    window.deskSync.getConfig(),
    window.deskSync.getStatus(),
    window.deskSync.getWslDistros(),
    window.deskSync.scanSkills(),
    window.deskSync.scanCommands()
  ]);

  return {
    config,
    status: { ...status, config },
    wslRuntime,
    inventory: { skills, commands }
  };
}

export function sortToolIds(tools: ToolId[]) {
  return [...tools].sort((left, right) => TOOL_IDS.indexOf(left) - TOOL_IDS.indexOf(right));
}
