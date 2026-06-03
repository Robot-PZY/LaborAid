import type { IntakeFormField } from '@/lib/intake-scenarios';

type Props = {
  fields: IntakeFormField[];
  values: Record<string, string>;
  onChange: (id: string, value: string) => void;
  disabled?: boolean;
};

export default function DynamicForm({ fields, values, onChange, disabled }: Props) {
  if (fields.length === 0) {
    return <p className="text-sm text-muted-foreground">该场景暂无表单配置。</p>;
  }

  return (
    <div className="space-y-4">
      {fields.map((field) => {
        const id = field.id;
        const value = values[id] ?? '';
        const label = (
          <label htmlFor={id} className="text-sm font-medium">
            {field.label}
            {field.required && <span className="ml-0.5 text-rose-600">*</span>}
          </label>
        );

        if (field.type === 'textarea') {
          return (
            <div key={id} className="space-y-1.5">
              {label}
              <textarea
                id={id}
                rows={4}
                maxLength={field.maxLength ?? 500}
                disabled={disabled}
                value={value}
                onChange={(e) => onChange(id, e.target.value)}
                placeholder={field.placeholder}
                className="input-field w-full resize-none"
              />
            </div>
          );
        }

        if (field.type === 'select' && field.options?.length) {
          return (
            <div key={id} className="space-y-1.5">
              {label}
              <select
                id={id}
                disabled={disabled}
                value={value}
                onChange={(e) => onChange(id, e.target.value)}
                className="input-field w-full"
              >
                <option value="">请选择</option>
                {field.options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          );
        }

        return (
          <div key={id} className="space-y-1.5">
            {label}
            <input
              id={id}
              type={field.type === 'number' ? 'number' : 'text'}
              disabled={disabled}
              value={value}
              onChange={(e) => onChange(id, e.target.value)}
              placeholder={field.placeholder}
              className="input-field w-full"
            />
          </div>
        );
      })}
    </div>
  );
}
