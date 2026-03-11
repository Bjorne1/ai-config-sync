import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes
} from 'react';
import { STATE_LABELS, TOOL_META, type DisplayState, type ToolId } from '../lib/models';

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

const STATE_STYLES: Record<DisplayState, string> = {
  healthy: 'border-emerald-900/30 bg-emerald-700/15 text-emerald-950',
  missing: 'border-amber-900/30 bg-amber-600/15 text-amber-950',
  conflict: 'border-red-950/30 bg-red-700/15 text-red-950',
  source_missing: 'border-red-950/30 bg-red-700/15 text-red-950',
  tool_unavailable: 'border-stone-900/30 bg-stone-800/10 text-stone-900',
  environment_error: 'border-red-950/30 bg-red-700/15 text-red-950',
  partial: 'border-sky-950/30 bg-sky-700/15 text-sky-950',
  idle: 'border-stone-900/20 bg-stone-800/5 text-stone-700'
};

const BUTTON_STYLES = {
  primary: 'border-stone-950 bg-stone-950 text-stone-50 hover:bg-[#be3e22]',
  secondary: 'border-stone-950/20 bg-stone-50 text-stone-900 hover:bg-stone-100',
  danger: 'border-red-950 bg-red-900 text-stone-50 hover:bg-red-800'
} as const;

export function Panel(props: {
  id: string;
  eyebrow: string;
  title: string;
  detail?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      id={props.id}
      className="relative overflow-hidden border-2 border-stone-950 bg-[#f9f2e8]/90 shadow-[10px_10px_0_0_#171717]"
    >
      <div className="absolute inset-0 bg-[linear-gradient(transparent_0,transparent_31px,rgba(23,23,23,0.04)_32px),linear-gradient(90deg,transparent_0,transparent_31px,rgba(23,23,23,0.04)_32px)] bg-[size:32px_32px]" />
      <div className="relative border-b-2 border-stone-950 bg-stone-950 px-5 py-4 text-stone-50">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.35em] text-stone-300">
              {props.eyebrow}
            </p>
            <h2 className="mt-2 font-['Georgia','Times_New_Roman',serif] text-3xl leading-none">
              {props.title}
            </h2>
            {props.detail ? <p className="mt-2 max-w-3xl text-sm text-stone-300">{props.detail}</p> : null}
          </div>
          {props.actions ? <div className="flex flex-wrap gap-2">{props.actions}</div> : null}
        </div>
      </div>
      <div className="relative px-5 py-5">{props.children}</div>
    </section>
  );
}

export function ActionButton(
  props: ButtonHTMLAttributes<HTMLButtonElement> & {
    busy?: boolean;
    variant?: keyof typeof BUTTON_STYLES;
  }
) {
  const { busy, className, children, disabled, variant = 'secondary', ...rest } = props;
  return (
    <button
      {...rest}
      disabled={disabled || busy}
      className={cx(
        'min-h-10 border px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45',
        BUTTON_STYLES[variant],
        className
      )}
    >
      {busy ? '处理中…' : children}
    </button>
  );
}

export function StateBadge({ state, label }: { state: DisplayState; label?: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center border px-2 py-1 font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.25em]",
        STATE_STYLES[state]
      )}
    >
      {label ?? STATE_LABELS[state]}
    </span>
  );
}

export function ToolChip(props: {
  toolId: ToolId;
  active: boolean;
  onClick?: () => void;
  disabled?: boolean;
}) {
  const meta = TOOL_META[props.toolId];
  return (
    <button
      disabled={props.disabled}
      onClick={props.onClick}
      className={cx(
        'flex min-w-28 flex-col border px-3 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-45',
        props.active
          ? 'border-stone-950 bg-[#be3e22] text-stone-50 shadow-[4px_4px_0_0_#171717]'
          : 'border-stone-950/20 bg-stone-50 text-stone-700 hover:border-stone-950 hover:text-stone-950'
      )}
    >
      <span className="font-['Courier_New',monospace] text-[10px] uppercase tracking-[0.35em]">{meta.code}</span>
      <span className="mt-1 text-sm font-semibold">{meta.label}</span>
      <span className="text-[11px] uppercase tracking-[0.25em] opacity-70">{meta.lane}</span>
    </button>
  );
}

export function StatTile(props: { label: string; value: string | number; note: string }) {
  return (
    <div className="border border-stone-950 bg-[#efe4d5] p-4 shadow-[4px_4px_0_0_#171717]">
      <p className="font-['Courier_New',monospace] text-[11px] uppercase tracking-[0.3em] text-stone-600">
        {props.label}
      </p>
      <p className="mt-3 font-['Georgia','Times_New_Roman',serif] text-4xl leading-none text-stone-950">
        {props.value}
      </p>
      <p className="mt-3 text-sm text-stone-700">{props.note}</p>
    </div>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement> & { value: string }) {
  return (
    <input
      {...props}
      className={cx(
        'min-h-11 w-full border border-stone-950/20 bg-stone-50 px-3 py-2 text-sm text-stone-950 outline-none transition focus:border-stone-950',
        props.className
      )}
    />
  );
}

export function TextSelect(props: SelectHTMLAttributes<HTMLSelectElement> & { value: string }) {
  return (
    <select
      {...props}
      className={cx(
        'min-h-11 w-full border border-stone-950/20 bg-stone-50 px-3 py-2 text-sm text-stone-950 outline-none transition focus:border-stone-950',
        props.className
      )}
    />
  );
}
