import { useDeferredValue, useEffect, useState } from 'react';
import { type ResourceRow } from '../lib/dashboard';
import { KIND_LABELS, TOOL_IDS, type ResourceKind, type ToolId } from '../lib/models';
import { ActionButton, Panel, StateBadge, TextInput, ToolChip } from './ui';

interface ResourceSectionProps {
  kind: ResourceKind;
  onRescan: () => Promise<void>;
  onSave: () => Promise<void>;
  onSync: (names: string[]) => Promise<void>;
  onToggleTool: (name: string, toolId: ToolId) => void;
  rows: ResourceRow[];
  busy: {
    rescan: boolean;
    save: boolean;
    sync: boolean;
  };
  dirty: boolean;
}

function matchesSearch(row: ResourceRow, query: string) {
  return row.name.toLowerCase().includes(query) || row.path.toLowerCase().includes(query);
}

function ResourceRowCard(props: {
  onSelect: () => void;
  onToggleTool: (toolId: ToolId) => void;
  row: ResourceRow;
  selected: boolean;
}) {
  return (
    <div className="border border-stone-950 bg-stone-50 p-4">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="flex gap-3">
          <button
            onClick={props.onSelect}
            className={`mt-1 h-5 w-5 border ${props.selected ? 'border-stone-950 bg-[#be3e22]' : 'border-stone-950/40 bg-stone-50'}`}
          />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-lg font-semibold text-stone-950">{props.row.name}</p>
              <StateBadge state={props.row.summaryState} />
              <StateBadge state={props.row.scanned ? 'healthy' : 'source_missing'} label={props.row.scanned ? '已扫描' : '未扫描'} />
            </div>
            <p className="mt-2 break-all text-sm text-stone-700">{props.row.path || '源路径不可用'}</p>
            <p className="mt-1 text-sm text-stone-500">
              {props.row.isDirectory ? '目录' : '文件'}
              {props.row.childrenCount > 0 ? ` · ${props.row.childrenCount} 个子项` : ''}
              {props.row.configuredTools.length > 0 ? ` · ${props.row.summaryMessage}` : ' · 尚未分配工具'}
            </p>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 xl:w-[420px]">
          {TOOL_IDS.map(toolId => (
            <ToolChip
              key={toolId}
              active={props.row.configuredTools.includes(toolId)}
              onClick={() => props.onToggleTool(toolId)}
              toolId={toolId}
            />
          ))}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {props.row.entries.length === 0 ? (
          <StateBadge state="idle" label="等待状态回填" />
        ) : (
          props.row.entries.map(entry => (
            <StateBadge
              key={`${entry.environmentId}:${entry.toolId}`}
              state={entry.state}
              label={`${entry.environmentId}/${entry.toolId}`}
            />
          ))
        )}
      </div>
    </div>
  );
}

export function ResourceSection(props: ResourceSectionProps) {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());
  const filteredRows = props.rows.filter(row => matchesSearch(row, deferredSearch));

  useEffect(() => {
    setSelected(current => current.filter(name => props.rows.some(row => row.name === name)));
  }, [props.rows]);

  const selectedVisible = filteredRows.filter(row => selected.includes(row.name)).map(row => row.name);

  return (
    <Panel
      id={props.kind}
      eyebrow={props.kind === 'skills' ? '02 / Skills' : '03 / Commands'}
      title={KIND_LABELS[props.kind]}
      detail="每行代表一个源资源；工具切换只修改分配草稿，保存后才写回后端配置。"
      actions={
        <>
          <ActionButton busy={props.busy.rescan} onClick={() => void props.onRescan()}>
            重扫源目录
          </ActionButton>
          <ActionButton busy={props.busy.save} onClick={() => void props.onSave()} variant="primary">
            保存分配
          </ActionButton>
          <ActionButton
            busy={props.busy.sync}
            disabled={selectedVisible.length === 0}
            onClick={() => void props.onSync(selectedVisible)}
          >
            同步勾选项
          </ActionButton>
        </>
      }
    >
      <div className="grid gap-4">
        <div className="grid gap-3 lg:grid-cols-[1fr,auto,auto]">
          <TextInput placeholder={`搜索 ${KIND_LABELS[props.kind]} 名称或路径`} value={search} onChange={event => setSearch(event.currentTarget.value)} />
          <ActionButton
            onClick={() =>
              setSelected(current =>
                filteredRows.every(row => current.includes(row.name))
                  ? current.filter(name => !filteredRows.some(row => row.name === name))
                  : Array.from(new Set([...current, ...filteredRows.map(row => row.name)]))
              )
            }
          >
            {filteredRows.every(row => selected.includes(row.name)) ? '取消可见项' : '全选可见项'}
          </ActionButton>
          <div className="flex items-center border border-stone-950 bg-[#efe3d2] px-3 text-sm text-stone-700">
            {props.rows.length} 条记录 · {props.dirty ? '存在未保存分配' : '分配已同步'}
          </div>
        </div>
        <div className="grid gap-3">
          {filteredRows.length === 0 ? (
            <div className="border border-dashed border-stone-950/30 bg-stone-50 px-4 py-8 text-center text-sm text-stone-600">
              没有匹配项。
            </div>
          ) : (
            filteredRows.map(row => (
              <ResourceRowCard
                key={row.name}
                onSelect={() =>
                  setSelected(current =>
                    current.includes(row.name) ? current.filter(name => name !== row.name) : [...current, row.name]
                  )
                }
                onToggleTool={toolId => props.onToggleTool(row.name, toolId)}
                row={row}
                selected={selected.includes(row.name)}
              />
            ))
          )}
        </div>
      </div>
    </Panel>
  );
}
