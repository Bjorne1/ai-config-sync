import { TOOL_IDS, TOOL_META, type ToolId } from '../lib/models';
import { TextInput } from './ui';

interface TargetGridProps {
  description: string;
  title: string;
  targets: Record<ToolId, string>;
  onChange: (toolId: ToolId, value: string) => void;
}

export function TargetGrid(props: TargetGridProps) {
  return (
    <div className="border border-stone-950 bg-[#efe3d2] p-4">
      <div className="mb-4">
        <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
          {props.title}
        </p>
        <p className="mt-2 text-sm text-stone-700">{props.description}</p>
      </div>
      <div className="grid gap-3">
        {TOOL_IDS.map(toolId => (
          <label key={toolId} className="grid gap-2 lg:grid-cols-[120px,1fr] lg:items-center">
            <span className="font-['Courier_New',monospace] text-xs uppercase tracking-[0.25em] text-stone-700">
              {TOOL_META[toolId].label}
            </span>
            <TextInput value={props.targets[toolId]} onChange={event => props.onChange(toolId, event.currentTarget.value)} />
          </label>
        ))}
      </div>
    </div>
  );
}
