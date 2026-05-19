import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import api from '@/lib/api';
import { useI18n } from '@/i18n/I18nProvider';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

type DeleteScope = 'all' | 'completed';

interface DeleteAllJobsButtonProps {
  scope: DeleteScope;
  onDeleted: () => void;
  variant?: 'history' | 'projects';
}

export function DeleteAllJobsButton({ scope, onDeleted, variant }: DeleteAllJobsButtonProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const copy = variant === 'projects' ? t.projects.deleteAll : t.history.deleteAll;

  const handleConfirm = async () => {
    setBusy(true);
    try {
      await api.delete('/jobs', { params: { confirm: 'DELETE_ALL', scope } });
      setOpen(false);
      onDeleted();
    } catch (error) {
      console.error('Bulk delete failed', error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
        >
          <Trash2 className="w-4 h-4 mr-2" />
          {copy.button}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent className="bg-slate-900 border-white/10 text-slate-100">
        <AlertDialogHeader>
          <AlertDialogTitle>{copy.title}</AlertDialogTitle>
          <AlertDialogDescription className="text-slate-400">{copy.description}</AlertDialogDescription>
        </AlertDialogHeader>
        <p className="text-xs font-mono text-red-400/90 px-1">{copy.phraseHint}</p>
        <AlertDialogFooter>
          <AlertDialogCancel className="border-white/10 bg-transparent hover:bg-white/5">
            {t.common.cancel}
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={busy}
            className="bg-red-600 hover:bg-red-500"
            onClick={(e) => {
              e.preventDefault();
              void handleConfirm();
            }}
          >
            {busy ? t.common.loading : copy.confirm}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
