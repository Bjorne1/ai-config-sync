import { summarizeCleanup } from '../lib/dashboard';
import type { CleanupResult } from '../lib/models';
import { ActionButton, Panel, StateBadge } from './ui';

interface CleanupSectionProps {
  busy: boolean;
  candidateCount: number;
  onRun: () => Promise<void>;
  result: CleanupResult | null;
}

export function CleanupSection(props: CleanupSectionProps) {
  return (
    <Panel
      id="cleanup"
      eyebrow="06 / Cleanup"
      title="清理工单"
      detail="清理会调用 `cleanupInvalid`，删除冲突、缺失或源失效的目标条目，并同步更新配置。"
      actions={
        <ActionButton busy={props.busy} onClick={() => void props.onRun()} variant="danger">
          执行清理
        </ActionButton>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[0.75fr,1.25fr]">
        <div className="border border-stone-950 bg-[#efe3d2] p-4">
          <StateBadge state={props.candidateCount > 0 ? 'conflict' : 'healthy'} label={props.candidateCount > 0 ? '待清理' : '无需清理'} />
          <p className="mt-4 font-['Georgia','Times_New_Roman',serif] text-5xl leading-none text-stone-950">
            {props.candidateCount}
          </p>
          <p className="mt-3 text-sm text-stone-700">来自状态面板中可被后端清理的异常目标数。</p>
        </div>
        <div className="border border-stone-950 bg-stone-50 p-4">
          <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
            最近清理结果
          </p>
          <p className="mt-3 text-sm text-stone-800">
            {props.result ? summarizeCleanup(props.result.cleaned) : '尚未执行清理。'}
          </p>
          <div className="mt-4 grid max-h-72 gap-2 overflow-auto">
            {props.result?.cleaned.map(item => (
              <div key={`${item.kind}:${item.name}:${item.toolId}:${item.environmentId}`} className="border border-stone-950/10 bg-[#efe3d2] px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{item.kind} / {item.name}</span>
                  <StateBadge state={item.success ? 'healthy' : 'conflict'} label={item.success ? '清理成功' : '清理失败'} />
                </div>
                <p className="mt-1 text-stone-700">{item.toolId} · {item.environmentId}</p>
                <p className="mt-1 break-all text-stone-500">{item.targetPath ?? '无目标路径'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}
