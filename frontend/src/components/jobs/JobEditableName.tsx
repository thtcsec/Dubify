import { useState } from 'react';
import { Pencil, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface JobEditableNameProps {
  jobId: string;
  filename: string;
  className?: string;
  onRenamed?: (name: string) => void;
}

export function JobEditableName({ jobId, filename, className = '', onRenamed }: JobEditableNameProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(filename);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const next = value.trim();
    if (!next || next === filename) {
      setEditing(false);
      setValue(filename);
      return;
    }
    setSaving(true);
    try {
      await api.patch(`/jobs/${jobId}`, { filename: next });
      onRenamed?.(next);
      setEditing(false);
    } catch {
      setValue(filename);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <div className={`flex items-center gap-1 min-w-0 ${className}`} onClick={(e) => e.stopPropagation()}>
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="h-7 text-xs bg-black/40 border-white/20"
          maxLength={200}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter') void save();
            if (e.key === 'Escape') {
              setValue(filename);
              setEditing(false);
            }
          }}
        />
        <Button type="button" size="icon" variant="ghost" className="h-7 w-7 shrink-0" disabled={saving} onClick={() => void save()}>
          <Check className="h-3.5 w-3.5 text-green-400" />
        </Button>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="h-7 w-7 shrink-0"
          onClick={() => {
            setValue(filename);
            setEditing(false);
          }}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-1 min-w-0 group/name ${className}`}>
      <span className="truncate font-semibold text-sm">{filename || 'Untitled'}</span>
      <button
        type="button"
        className="opacity-0 group-hover/name:opacity-100 p-0.5 text-slate-500 hover:text-cyan-400 shrink-0"
        title="Rename"
        onClick={(e) => {
          e.stopPropagation();
          setValue(filename);
          setEditing(true);
        }}
      >
        <Pencil className="h-3 w-3" />
      </button>
    </div>
  );
}
