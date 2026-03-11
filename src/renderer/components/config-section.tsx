import { TOOL_IDS, type ConfigFormState, type ResourceKind, type ToolId, type WslRuntime } from '../lib/models';
import { ActionButton, Panel, StateBadge, TextInput, TextSelect } from './ui';
import { TargetGrid } from './target-grid';

interface ConfigSectionProps {
  dirty: boolean;
  draft: ConfigFormState;
  onChange: (next: ConfigFormState) => void;
  onReloadWsl: () => Promise<void>;
  onSave: () => Promise<void>;
  reloadBusy: boolean;
  saveBusy: boolean;
  wslRuntime: WslRuntime;
}

function updateTargets(
  draft: ConfigFormState,
  environmentId: 'windows' | 'wsl',
  kind: ResourceKind,
  toolId: ToolId,
  value: string
) {
  return {
    ...draft,
    environments: {
      ...draft.environments,
      [environmentId]: {
        ...draft.environments[environmentId],
        targets: {
          ...draft.environments[environmentId].targets,
          [kind]: {
            ...draft.environments[environmentId].targets[kind],
            [toolId]: value
          }
        }
      }
    }
  };
}

function ToggleRow(props: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={props.onClick}
      className={`border px-3 py-2 text-sm font-semibold transition ${
        props.active ? 'border-stone-950 bg-stone-950 text-stone-50' : 'border-stone-950/20 bg-stone-50 text-stone-700'
      }`}
    >
      {props.label}
    </button>
  );
}

export function ConfigSection(props: ConfigSectionProps) {
  const { draft } = props;

  return (
    <Panel
      id="config"
      eyebrow="05 / Configuration"
      title="配置矩阵"
      detail="这里编辑会直接走 `saveConfig`，保留当前后端 IPC 契约，不在前端偷偷兜底。"
      actions={
        <>
          <ActionButton busy={props.reloadBusy} onClick={() => void props.onReloadWsl()}>
            重载 WSL 列表
          </ActionButton>
          <ActionButton busy={props.saveBusy} onClick={() => void props.onSave()} variant="primary">
            保存配置
          </ActionButton>
        </>
      }
    >
      <div className="grid gap-5">
        <div className="grid gap-4 xl:grid-cols-[0.95fr,1.05fr]">
          <div className="border border-stone-950 bg-[#efe3d2] p-4">
            <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
              Sync Mode
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <ToggleRow
                active={draft.syncMode === 'symlink'}
                label="Symlink"
                onClick={() => props.onChange({ ...draft, syncMode: 'symlink' })}
              />
              <ToggleRow
                active={draft.syncMode === 'copy'}
                label="Copy"
                onClick={() => props.onChange({ ...draft, syncMode: 'copy' })}
              />
            </div>
            <p className="mt-4 text-sm text-stone-700">
              `symlink` 更轻，`copy` 更独立。当前页面只提交真实配置，不对模式做额外限制。
            </p>
          </div>
          <div className="grid gap-3 border border-stone-950 bg-[#efe3d2] p-4">
            <label className="grid gap-2">
              <span className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                Skills Source Dir
              </span>
              <TextInput
                value={draft.sourceDirs.skills}
                onChange={event =>
                  props.onChange({
                    ...draft,
                    sourceDirs: { ...draft.sourceDirs, skills: event.currentTarget.value }
                  })
                }
              />
            </label>
            <label className="grid gap-2">
              <span className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                Commands Source Dir
              </span>
              <TextInput
                value={draft.sourceDirs.commands}
                onChange={event =>
                  props.onChange({
                    ...draft,
                    sourceDirs: { ...draft.sourceDirs, commands: event.currentTarget.value }
                  })
                }
              />
            </label>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1fr,1fr]">
          <div className="border border-stone-950 bg-[#efe3d2] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                  Windows
                </p>
                <p className="mt-2 text-sm text-stone-700">Windows 目标固定启用，路径可编辑。</p>
              </div>
              <StateBadge state="healthy" label="Always On" />
            </div>
          </div>
          <div className="border border-stone-950 bg-[#efe3d2] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                  WSL
                </p>
                <p className="mt-2 text-sm text-stone-700">
                  发行版列表来自 `getWslDistros`，错误直接展示，不做静默忽略。
                </p>
              </div>
              <ToggleRow
                active={draft.environments.wsl.enabled}
                label={draft.environments.wsl.enabled ? 'Enabled' : 'Disabled'}
                onClick={() =>
                  props.onChange({
                    ...draft,
                    environments: {
                      ...draft.environments,
                      wsl: {
                        ...draft.environments.wsl,
                        enabled: !draft.environments.wsl.enabled
                      }
                    }
                  })
                }
              />
            </div>
            <div className="mt-4 grid gap-3">
              <label className="grid gap-2">
                <span className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                  Selected Distro
                </span>
                <TextSelect
                  value={draft.environments.wsl.selectedDistro ?? ''}
                  onChange={event =>
                    props.onChange({
                      ...draft,
                      environments: {
                        ...draft.environments,
                        wsl: {
                          ...draft.environments.wsl,
                          selectedDistro: event.currentTarget.value || null
                        }
                      }
                    })
                  }
                >
                  <option value="">未选择</option>
                  {props.wslRuntime.distros.map(distro => (
                    <option key={distro} value={distro}>
                      {distro}
                    </option>
                  ))}
                </TextSelect>
              </label>
              <p className="text-sm text-stone-700">Home: {props.wslRuntime.homeDir ?? '未解析'}</p>
              {props.wslRuntime.error ? <p className="text-sm text-red-900">{props.wslRuntime.error}</p> : null}
            </div>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <TargetGrid
            description="Windows Skills 目标目录"
            title="Windows / Skills"
            targets={draft.environments.windows.targets.skills}
            onChange={(toolId, value) => props.onChange(updateTargets(draft, 'windows', 'skills', toolId, value))}
          />
          <TargetGrid
            description="Windows Commands 目标目录"
            title="Windows / Commands"
            targets={draft.environments.windows.targets.commands}
            onChange={(toolId, value) => props.onChange(updateTargets(draft, 'windows', 'commands', toolId, value))}
          />
          <TargetGrid
            description="WSL Skills 目标目录"
            title="WSL / Skills"
            targets={draft.environments.wsl.targets.skills}
            onChange={(toolId, value) => props.onChange(updateTargets(draft, 'wsl', 'skills', toolId, value))}
          />
          <TargetGrid
            description="WSL Commands 目标目录"
            title="WSL / Commands"
            targets={draft.environments.wsl.targets.commands}
            onChange={(toolId, value) => props.onChange(updateTargets(draft, 'wsl', 'commands', toolId, value))}
          />
        </div>

        <div className="border border-stone-950 bg-[#efe3d2] p-4">
          <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
            Command Folder Support
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <ToggleRow
              active={draft.commandSubfolderSupport.default}
              label={`默认 ${draft.commandSubfolderSupport.default ? '保留目录' : '拍平目录'}`}
              onClick={() =>
                props.onChange({
                  ...draft,
                  commandSubfolderSupport: {
                    ...draft.commandSubfolderSupport,
                    default: !draft.commandSubfolderSupport.default
                  }
                })
              }
            />
            {TOOL_IDS.map(toolId => (
              <ToggleRow
                key={toolId}
                active={Boolean(draft.commandSubfolderSupport.tools[toolId])}
                label={`${toolId} ${draft.commandSubfolderSupport.tools[toolId] ? '目录' : '拍平'}`}
                onClick={() =>
                  props.onChange({
                    ...draft,
                    commandSubfolderSupport: {
                      ...draft.commandSubfolderSupport,
                      tools: {
                        ...draft.commandSubfolderSupport.tools,
                        [toolId]: !draft.commandSubfolderSupport.tools[toolId]
                      }
                    }
                  })
                }
              />
            ))}
          </div>
        </div>

        {props.dirty ? <p className="text-sm text-stone-700">存在未保存配置改动。</p> : null}
      </div>
    </Panel>
  );
}
