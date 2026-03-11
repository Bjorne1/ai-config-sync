import { getOverviewStats } from '../lib/dashboard';
import type { ActionLogEntry, DashboardSnapshot } from '../lib/models';
import { ActionButton, Panel, StateBadge, StatTile } from './ui';

interface OverviewSectionProps {
  candidateCount: number;
  issueCount: number;
  latestLog: ActionLogEntry | null;
  lastSyncSummary: string | null;
  onRefresh: () => Promise<void>;
  onSyncAll: () => Promise<void>;
  refreshBusy: boolean;
  snapshot: DashboardSnapshot;
  syncBusy: boolean;
}

export function OverviewSection(props: OverviewSectionProps) {
  const stats = getOverviewStats(props.snapshot, props.issueCount, props.candidateCount);

  return (
    <Panel
      id="overview"
      eyebrow="01 / Overview"
      title="编辑部总控台"
      detail="把 Skills、Commands、目标环境和工具更新放进一张工业工单里，所有状态一眼看穿。"
      actions={
        <>
          <ActionButton busy={props.refreshBusy} onClick={() => void props.onRefresh()}>
            刷新总览
          </ActionButton>
          <ActionButton busy={props.syncBusy} onClick={() => void props.onSyncAll()} variant="primary">
            同步全部资源
          </ActionButton>
        </>
      }
    >
      <div className="grid gap-5 xl:grid-cols-[1.35fr,1fr]">
        <div className="border border-stone-950 bg-[#e9ddcd] p-5 shadow-[6px_6px_0_0_#171717]">
          <div className="flex flex-wrap items-center gap-2">
            <StateBadge state={props.snapshot.config.syncMode === 'copy' ? 'partial' : 'healthy'} label={props.snapshot.config.syncMode === 'copy' ? 'COPY' : 'SYMLINK'} />
            <StateBadge
              state={props.snapshot.config.environments.wsl.enabled ? 'partial' : 'idle'}
              label={props.snapshot.config.environments.wsl.enabled ? 'WSL ON' : 'WSL OFF'}
            />
            <StateBadge state={props.issueCount > 0 ? 'conflict' : 'healthy'} label={props.issueCount > 0 ? '需处理' : '运行平稳'} />
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-[1fr,240px]">
            <div>
              <p className="font-['Georgia','Times_New_Roman',serif] text-5xl leading-none text-stone-950">
                AI Config Sync
              </p>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-stone-800">
                工具目录、源目录、跨 Windows / WSL 目标、清理动作与更新日志都落在同一个现场。你看到的是一块
                工业风作业板，不是默认后台壳子。
              </p>
            </div>
            <div className="border border-stone-950 bg-stone-950 p-4 text-stone-50">
              <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-400">
                最近动作
              </p>
              <p className="mt-4 text-lg font-semibold">{props.latestLog?.label ?? '尚未执行动作'}</p>
              <p className="mt-2 text-sm text-stone-300">{props.latestLog?.detail ?? '等待首次 IPC 调用。'}</p>
              <p className="mt-4 text-[11px] uppercase tracking-[0.3em] text-stone-500">
                {props.latestLog?.time ?? '--:--:--'}
              </p>
            </div>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="border border-stone-950/20 bg-stone-50 px-4 py-3">
              <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                Source Deck
              </p>
              <p className="mt-2 text-sm text-stone-800">{props.snapshot.config.sourceDirs.skills}</p>
              <p className="mt-1 text-sm text-stone-800">{props.snapshot.config.sourceDirs.commands}</p>
            </div>
            <div className="border border-stone-950/20 bg-stone-50 px-4 py-3">
              <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
                最近同步
              </p>
              <p className="mt-2 text-sm text-stone-800">{props.lastSyncSummary ?? '尚未执行同步批次'}</p>
              <p className="mt-1 text-sm text-stone-500">
                WSL 发行版：{props.snapshot.wslRuntime.selectedDistro ?? '未启用'}
              </p>
            </div>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {stats.map(stat => (
            <StatTile key={stat.label} label={stat.label} note={stat.note} value={stat.value} />
          ))}
        </div>
      </div>
    </Panel>
  );
}
