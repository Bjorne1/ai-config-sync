import { formatKindName, type IssueRow } from '../lib/dashboard';
import type { ActionLogEntry, DashboardSnapshot } from '../lib/models';
import { Panel, StateBadge } from './ui';

interface StatusSectionProps {
  issues: IssueRow[];
  lastSyncSummary: string | null;
  logs: ActionLogEntry[];
  snapshot: DashboardSnapshot;
}

export function StatusSection(props: StatusSectionProps) {
  const environments = Object.values(props.snapshot.status.environments);

  return (
    <Panel
      id="status"
      eyebrow="04 / Status"
      title="状态台账"
      detail="环境解析、资源异常和最近动作按工单方式排布，便于直接判断哪里需要补刀。"
    >
      <div className="grid gap-4 xl:grid-cols-[0.9fr,1.1fr]">
        <div className="grid gap-4">
          {environments.map(environment => (
            <div key={environment.id} className="border border-stone-950 bg-[#efe3d2] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                    {environment.id}
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-stone-950">{environment.label}</p>
                </div>
                <StateBadge
                  state={environment.error ? 'environment_error' : environment.enabled ? 'healthy' : 'idle'}
                  label={environment.error ? '异常' : environment.enabled ? '启用' : '关闭'}
                />
              </div>
              <p className="mt-4 text-sm text-stone-700">
                {environment.error ?? `Skills 根目录：${environment.targets.skills.claude ?? '不可用'}`}
              </p>
              <p className="mt-2 text-sm text-stone-500">
                Commands 根目录：{environment.targets.commands.codex ?? '不可用'}
              </p>
            </div>
          ))}
          <div className="border border-stone-950 bg-stone-950 p-4 text-stone-50">
            <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-400">
              最近同步摘要
            </p>
            <p className="mt-3 text-sm text-stone-200">{props.lastSyncSummary ?? '尚未同步'}</p>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="border border-stone-950 bg-stone-50 p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                异常列表
              </p>
              <StateBadge state={props.issues.length > 0 ? 'conflict' : 'healthy'} label={`${props.issues.length} 条`} />
            </div>
            <div className="mt-4 grid max-h-80 gap-2 overflow-auto">
              {props.issues.length === 0 ? (
                <p className="text-sm text-stone-600">没有异常条目。</p>
              ) : (
                props.issues.slice(0, 12).map(issue => (
                  <div key={issue.id} className="border border-stone-950/10 bg-[#efe3d2] px-3 py-2 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-stone-950">{formatKindName(issue.kind, issue.name)}</span>
                      <StateBadge state={issue.state} />
                    </div>
                    <p className="mt-1 text-stone-700">
                      {issue.environmentId} · {issue.toolId} · {issue.itemCount} 项
                    </p>
                    <p className="mt-1 break-all text-stone-500">{issue.targetPath ?? issue.message}</p>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="border border-stone-950 bg-stone-50 p-4">
            <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
              动作日志
            </p>
            <div className="mt-4 grid gap-2">
              {props.logs.length === 0 ? (
                <p className="text-sm text-stone-600">暂无日志。</p>
              ) : (
                props.logs.map(log => (
                  <div key={log.id} className="border border-stone-950/10 bg-[#efe3d2] px-3 py-2 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-stone-950">{log.label}</span>
                      <StateBadge state={log.status === 'ok' ? 'healthy' : 'conflict'} label={log.time} />
                    </div>
                    <p className="mt-1 text-stone-700">{log.detail}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
