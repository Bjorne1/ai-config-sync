export const TOOL_META = {
  claude: { code: 'CL', label: 'Claude', lane: 'Desk' },
  codex: { code: 'CX', label: 'Codex', lane: 'Forge' },
  gemini: { code: 'GM', label: 'Gemini', lane: 'Relay' },
  antigravity: { code: 'AG', label: 'Antigravity', lane: 'Lab' }
} as const;

export type ToolId = keyof typeof TOOL_META;
export const TOOL_IDS = Object.keys(TOOL_META) as ToolId[];

export type ResourceKind = 'skills' | 'commands';
export type SyncMode = 'symlink' | 'copy';
export type HealthState =
  | 'healthy'
  | 'missing'
  | 'conflict'
  | 'source_missing'
  | 'tool_unavailable'
  | 'environment_error'
  | 'partial';
export type DisplayState = HealthState | 'idle';

export const KIND_LABELS: Record<ResourceKind, string> = {
  skills: 'Skills',
  commands: 'Commands'
};

export const STATE_LABELS: Record<DisplayState, string> = {
  healthy: '已同步',
  missing: '目标缺失',
  conflict: '存在冲突',
  source_missing: '源不存在',
  tool_unavailable: '工具未安装',
  environment_error: '环境异常',
  partial: '部分完成',
  idle: '未分配'
};

export type ToolPathMap = Record<ToolId, string>;
export type ResourceAssignments = Record<string, ToolId[]>;

export interface SourceDirs {
  skills: string;
  commands: string;
}

export interface CommandSubfolderSupport {
  default: boolean;
  tools: Partial<Record<ToolId, boolean>>;
}

export interface WindowsEnvironmentConfig {
  enabled: true;
  targets: Record<ResourceKind, ToolPathMap>;
}

export interface WslEnvironmentConfig {
  enabled: boolean;
  selectedDistro: string | null;
  targets: Record<ResourceKind, ToolPathMap>;
}

export interface AppConfig {
  version: number;
  syncMode: SyncMode;
  sourceDirs: SourceDirs;
  environments: {
    windows: WindowsEnvironmentConfig;
    wsl: WslEnvironmentConfig;
  };
  resources: Record<ResourceKind, ResourceAssignments>;
  commandSubfolderSupport: CommandSubfolderSupport;
  updateTools: Record<string, UpdateToolDefinition>;
}

export interface ConfigFormState {
  syncMode: SyncMode;
  sourceDirs: SourceDirs;
  environments: AppConfig['environments'];
  commandSubfolderSupport: CommandSubfolderSupport;
}

export type UpdateToolDefinition =
  | { type: 'npm'; package: string }
  | { type: 'custom'; command: string };

export interface WslRuntime {
  available: boolean;
  distros: string[];
  selectedDistro: string | null;
  homeDir: string | null;
  error: string | null;
}

export interface EnvironmentStatus {
  id: 'windows' | 'wsl';
  enabled: boolean;
  label: string;
  rawTargets: Record<ResourceKind, ToolPathMap>;
  roots: Record<ToolId, string | null>;
  targets: Record<ResourceKind, ToolPathMap>;
  error: string | null;
  meta?: WslRuntime;
}

export interface ResourceEntryStatus {
  environmentId: EnvironmentStatus['id'];
  toolId: ToolId;
  state: HealthState;
  message: string;
  itemCount: number;
  targetPath: string | null;
}

export interface ResourceStatus {
  kind: ResourceKind;
  name: string;
  sourcePath: string;
  isDirectory: boolean;
  configuredTools: ToolId[];
  entries: ResourceEntryStatus[];
}

export interface StatusSnapshot {
  config: AppConfig;
  environments: Record<'windows' | 'wsl', EnvironmentStatus>;
  skills: ResourceStatus[];
  commands: ResourceStatus[];
}

export interface SkillScanEntry {
  name: string;
  path: string;
  isDirectory: boolean;
}

export interface CommandScanEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  parent: string | null;
  children: string[];
}

export type ResourceInventoryEntry = SkillScanEntry | CommandScanEntry;

export interface SyncDetail {
  kind: ResourceKind;
  name: string;
  toolId: ToolId;
  environmentId: EnvironmentStatus['id'];
  targetPath?: string;
  success: boolean;
  skipped?: boolean;
  message: string;
}

export interface CleanupDetail {
  kind: ResourceKind;
  name: string;
  toolId: ToolId;
  environmentId: EnvironmentStatus['id'];
  targetPath: string | null;
  state: HealthState;
  success: boolean;
  message: string;
}

export interface CleanupResult {
  cleaned: CleanupDetail[];
  config: AppConfig;
}

export interface ToolUpdateResult {
  name: string;
  type: UpdateToolDefinition['type'];
  versionBefore: string | null;
  versionAfter: string | null;
  success: boolean;
}

export interface DashboardSnapshot {
  config: AppConfig;
  status: StatusSnapshot;
  wslRuntime: WslRuntime;
  inventory: {
    skills: SkillScanEntry[];
    commands: CommandScanEntry[];
  };
}

export interface ActionLogEntry {
  id: string;
  label: string;
  detail: string;
  status: 'ok' | 'error';
  time: string;
}

export interface DeskSyncApi {
  cleanupInvalid(): Promise<CleanupResult>;
  getConfig(): Promise<AppConfig>;
  getStatus(): Promise<StatusSnapshot>;
  getWslDistros(): Promise<WslRuntime>;
  replaceResourceMap(kind: ResourceKind, assignments: ResourceAssignments): Promise<AppConfig>;
  saveConfig(patch: Partial<AppConfig>): Promise<AppConfig>;
  scanCommands(): Promise<CommandScanEntry[]>;
  scanSkills(): Promise<SkillScanEntry[]>;
  syncAll(): Promise<Record<ResourceKind, SyncDetail[]>>;
  syncResources(kind: ResourceKind, names: string[]): Promise<SyncDetail[]>;
  updateTools(): Promise<ToolUpdateResult[]>;
}
