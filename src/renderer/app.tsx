import { startTransition, useEffect, useState } from 'react';
import {
  buildIssueRows,
  buildResourceRows,
  cloneAssignments,
  createLogEntry,
  fetchDashboardSnapshot,
  getConfigFormState,
  getConfigPatch,
  getErrorMessage,
  serialize,
  sortToolIds,
  summarizeSyncDetails
} from './lib/dashboard';
import type {
  ActionLogEntry,
  CleanupResult,
  ConfigFormState,
  DashboardSnapshot,
  ResourceAssignments,
  ResourceKind,
  ToolId,
  ToolUpdateResult
} from './lib/models';
import { CleanupSection } from './components/cleanup-section';
import { ConfigSection } from './components/config-section';
import { OverviewSection } from './components/overview-section';
import { ResourceSection } from './components/resource-section';
import { StatusSection } from './components/status-section';
import { ToolsSection } from './components/tools-section';

type BusyState = Record<string, boolean>;

export function App() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [configDraft, setConfigDraft] = useState<ConfigFormState | null>(null);
  const [resourceDrafts, setResourceDrafts] = useState<Record<ResourceKind, ResourceAssignments> | null>(null);
  const [busy, setBusy] = useState<BusyState>({ initial: true });
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<ActionLogEntry[]>([]);
  const [lastSyncSummary, setLastSyncSummary] = useState<string | null>(null);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const [toolResults, setToolResults] = useState<ToolUpdateResult[]>([]);

  useEffect(() => {
    void refreshSnapshot({ resetConfig: true, resetResources: true }, 'initial');
  }, []);

  async function refreshSnapshot(
    reset: { resetConfig: boolean; resetResources: boolean },
    key = 'refresh'
  ) {
    setBusy(current => ({ ...current, [key]: true }));
    setError(null);

    try {
      const next = await fetchDashboardSnapshot();
      startTransition(() => {
        setSnapshot(next);
        if (reset.resetConfig) {
          setConfigDraft(getConfigFormState(next.config));
        }
        if (reset.resetResources) {
          setResourceDrafts({
            skills: cloneAssignments(next.config.resources.skills),
            commands: cloneAssignments(next.config.resources.commands)
          });
        }
      });
    } catch (caught) {
      const message = getErrorMessage(caught);
      setError(message);
      setLogs(current => [createLogEntry('刷新失败', message, 'error'), ...current].slice(0, 6));
    } finally {
      setBusy(current => ({ ...current, [key]: false }));
    }
  }

  async function runAction<T>(
    key: string,
    label: string,
    task: () => Promise<T>,
    onSuccess: (result: T) => Promise<void> | void
  ) {
    setBusy(current => ({ ...current, [key]: true }));
    setError(null);

    try {
      const result = await task();
      await onSuccess(result);
      setLogs(current => [createLogEntry(label, '执行完成', 'ok'), ...current].slice(0, 6));
    } catch (caught) {
      const message = getErrorMessage(caught);
      setError(`${label}: ${message}`);
      setLogs(current => [createLogEntry(label, message, 'error'), ...current].slice(0, 6));
    } finally {
      setBusy(current => ({ ...current, [key]: false }));
    }
  }

  function toggleAssignment(kind: ResourceKind, name: string, toolId: ToolId) {
    setResourceDrafts(current => {
      if (!current) {
        return current;
      }

      const group = { ...current[kind] };
      const currentTools = group[name] ?? [];
      const nextTools = currentTools.includes(toolId)
        ? currentTools.filter(item => item !== toolId)
        : sortToolIds([...currentTools, toolId]);

      if (nextTools.length === 0) {
        delete group[name];
      } else {
        group[name] = nextTools;
      }

      return { ...current, [kind]: group };
    });
  }

  if (!snapshot || !configDraft || !resourceDrafts) {
    return (
      <div className="min-h-screen bg-[#e7dbca] p-8 text-stone-950">
        <div className="mx-auto max-w-5xl border-2 border-stone-950 bg-[#f9f2e8] p-8 shadow-[12px_12px_0_0_#171717]">
          <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.35em] text-stone-600">
            Rendering Deck
          </p>
          <p className="mt-6 font-['Georgia','Times_New_Roman',serif] text-6xl leading-none">
            {busy.initial ? '正在装载渲染层…' : '初始化失败'}
          </p>
          {error ? <p className="mt-4 text-sm text-red-900">{error}</p> : null}
        </div>
      </div>
    );
  }

  const issues = buildIssueRows(snapshot);
  const skillsRows = buildResourceRows('skills', snapshot.inventory.skills, resourceDrafts.skills, snapshot.status.skills);
  const commandsRows = buildResourceRows('commands', snapshot.inventory.commands, resourceDrafts.commands, snapshot.status.commands);
  const configDirty = serialize(configDraft) !== serialize(getConfigFormState(snapshot.config));
  const skillsDirty = serialize(resourceDrafts.skills) !== serialize(snapshot.config.resources.skills);
  const commandsDirty = serialize(resourceDrafts.commands) !== serialize(snapshot.config.resources.commands);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(190,62,34,0.16),transparent_25%),linear-gradient(135deg,#f3ecdf_0%,#ddcfbd_100%)] text-stone-950">
      <div className="mx-auto grid max-w-[1700px] gap-6 px-4 py-5 xl:grid-cols-[260px,minmax(0,1fr)]">
        <aside className="xl:sticky xl:top-4 xl:h-[calc(100vh-2rem)]">
          <div className="border-2 border-stone-950 bg-stone-950 p-5 text-stone-50 shadow-[10px_10px_0_0_#171717]">
            <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.35em] text-stone-400">
              Boss Console
            </p>
            <p className="mt-4 font-['Georgia','Times_New_Roman',serif] text-4xl leading-none">Renderer</p>
            <p className="mt-4 text-sm leading-7 text-stone-300">
              编辑部排版骨架 + 工业作业板，所有动作都映射到现有 IPC。
            </p>
            <nav className="mt-6 grid gap-2 text-sm">
              {[
                ['overview', '概览'],
                ['skills', 'Skills'],
                ['commands', 'Commands'],
                ['status', '状态'],
                ['config', '配置'],
                ['cleanup', '清理'],
                ['tools', '工具更新']
              ].map(([id, label]) => (
                <a key={id} className="border border-stone-50/15 px-3 py-2 hover:bg-stone-50/10" href={`#${id}`}>
                  {label}
                </a>
              ))}
            </nav>
            {error ? <p className="mt-6 border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">{error}</p> : null}
          </div>
        </aside>

        <main className="grid gap-6">
          <OverviewSection
            candidateCount={issues.filter(issue => ['conflict', 'missing', 'source_missing'].includes(issue.state)).length}
            issueCount={issues.length}
            latestLog={logs[0] ?? null}
            lastSyncSummary={lastSyncSummary}
            onRefresh={() => refreshSnapshot({ resetConfig: false, resetResources: false })}
            onSyncAll={() =>
              runAction('syncAll', '全量同步', () => window.deskSync.syncAll(), async result => {
                setLastSyncSummary(
                  `Skills ${summarizeSyncDetails(result.skills)}；Commands ${summarizeSyncDetails(result.commands)}`
                );
                await refreshSnapshot({ resetConfig: false, resetResources: false }, 'refreshAfterSyncAll');
              })
            }
            refreshBusy={Boolean(busy.refresh)}
            snapshot={snapshot}
            syncBusy={Boolean(busy.syncAll)}
          />

          <ResourceSection
            busy={{
              rescan: Boolean(busy.scanSkills),
              save: Boolean(busy.saveSkills),
              sync: Boolean(busy.syncSkills)
            }}
            dirty={skillsDirty}
            kind="skills"
            onRescan={() => refreshSnapshot({ resetConfig: false, resetResources: false }, 'scanSkills')}
            onSave={() =>
              runAction('saveSkills', '保存 Skills 分配', () => window.deskSync.replaceResourceMap('skills', resourceDrafts.skills), async () => {
                await refreshSnapshot({ resetConfig: false, resetResources: true }, 'refreshAfterSaveSkills');
              })
            }
            onSync={names =>
              runAction('syncSkills', '同步 Skills', () => window.deskSync.syncResources('skills', names), async result => {
                setLastSyncSummary(`Skills ${summarizeSyncDetails(result)}`);
                await refreshSnapshot({ resetConfig: false, resetResources: false }, 'refreshAfterSyncSkills');
              })
            }
            onToggleTool={(name, toolId) => toggleAssignment('skills', name, toolId)}
            rows={skillsRows}
          />

          <ResourceSection
            busy={{
              rescan: Boolean(busy.scanCommands),
              save: Boolean(busy.saveCommands),
              sync: Boolean(busy.syncCommands)
            }}
            dirty={commandsDirty}
            kind="commands"
            onRescan={() => refreshSnapshot({ resetConfig: false, resetResources: false }, 'scanCommands')}
            onSave={() =>
              runAction(
                'saveCommands',
                '保存 Commands 分配',
                () => window.deskSync.replaceResourceMap('commands', resourceDrafts.commands),
                async () => {
                  await refreshSnapshot({ resetConfig: false, resetResources: true }, 'refreshAfterSaveCommands');
                }
              )
            }
            onSync={names =>
              runAction('syncCommands', '同步 Commands', () => window.deskSync.syncResources('commands', names), async result => {
                setLastSyncSummary(`Commands ${summarizeSyncDetails(result)}`);
                await refreshSnapshot({ resetConfig: false, resetResources: false }, 'refreshAfterSyncCommands');
              })
            }
            onToggleTool={(name, toolId) => toggleAssignment('commands', name, toolId)}
            rows={commandsRows}
          />

          <StatusSection issues={issues} lastSyncSummary={lastSyncSummary} logs={logs} snapshot={snapshot} />

          <ConfigSection
            dirty={configDirty}
            draft={configDraft}
            onChange={setConfigDraft}
            onReloadWsl={() => refreshSnapshot({ resetConfig: false, resetResources: false }, 'reloadWsl')}
            onSave={() =>
              runAction('saveConfig', '保存配置', () => window.deskSync.saveConfig(getConfigPatch(configDraft)), async () => {
                await refreshSnapshot({ resetConfig: true, resetResources: false }, 'refreshAfterSaveConfig');
              })
            }
            reloadBusy={Boolean(busy.reloadWsl)}
            saveBusy={Boolean(busy.saveConfig)}
            wslRuntime={snapshot.wslRuntime}
          />

          <CleanupSection
            busy={Boolean(busy.cleanup)}
            candidateCount={issues.filter(issue => ['conflict', 'missing', 'source_missing'].includes(issue.state)).length}
            onRun={() =>
              runAction('cleanup', '执行清理', () => window.deskSync.cleanupInvalid(), async result => {
                setCleanupResult(result);
                await refreshSnapshot({ resetConfig: false, resetResources: true }, 'refreshAfterCleanup');
              })
            }
            result={cleanupResult}
          />

          <ToolsSection
            busy={Boolean(busy.updateTools)}
            definitions={snapshot.config.updateTools}
            onRun={() =>
              runAction('updateTools', '更新工具', () => window.deskSync.updateTools(), result => {
                setToolResults(result);
              })
            }
            results={toolResults}
          />
        </main>
      </div>
    </div>
  );
}
