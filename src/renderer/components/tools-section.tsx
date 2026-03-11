import type { ToolUpdateResult, UpdateToolDefinition } from '../lib/models';
import { ActionButton, Panel, StateBadge } from './ui';

interface ToolsSectionProps {
  busy: boolean;
  definitions: Record<string, UpdateToolDefinition>;
  onRun: () => Promise<void>;
  results: ToolUpdateResult[];
}

export function ToolsSection(props: ToolsSectionProps) {
  const entries = Object.entries(props.definitions);

  return (
    <Panel
      id="tools"
      eyebrow="07 / Tool Update"
      title="工具更新"
      detail="更新项来自配置里的 `updateTools`，执行结果原样展示，方便定位 npm 包和自定义命令。"
      actions={
        <ActionButton busy={props.busy} onClick={() => void props.onRun()} variant="primary">
          一键更新工具
        </ActionButton>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[0.95fr,1.05fr]">
        <div className="grid gap-3">
          {entries.map(([name, definition]) => (
            <div key={name} className="border border-stone-950 bg-[#efe3d2] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-lg font-semibold text-stone-950">{name}</p>
                <StateBadge state="partial" label={definition.type.toUpperCase()} />
              </div>
              <p className="mt-3 break-all text-sm text-stone-700">
                {'package' in definition ? definition.package : definition.command}
              </p>
            </div>
          ))}
        </div>
        <div className="border border-stone-950 bg-stone-50 p-4">
          <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
            最近更新结果
          </p>
          <div className="mt-4 grid max-h-80 gap-3 overflow-auto">
            {props.results.length === 0 ? (
              <p className="text-sm text-stone-600">尚未执行更新。</p>
            ) : (
              props.results.map(result => (
                <div key={result.name} className="border border-stone-950/10 bg-[#efe3d2] p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-stone-950">{result.name}</span>
                    <StateBadge state={result.success ? 'healthy' : 'conflict'} label={result.success ? '成功' : '失败'} />
                  </div>
                  <p className="mt-2 text-sm text-stone-700">{result.type}</p>
                  <p className="mt-1 text-sm text-stone-500">
                    {result.versionBefore ?? 'n/a'} → {result.versionAfter ?? 'n/a'}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}
