export const CHANNEL_THEME: Record<
  string,
  { border: string; chip: string; dot: string }
> = {
  'migrant-worker': {
    border: 'border-l-amber-500',
    chip: 'bg-amber-500/12 text-amber-900 dark:text-amber-100',
    dot: 'bg-amber-500',
  },
  'intern-probation': {
    border: 'border-l-sky-500',
    chip: 'bg-sky-500/12 text-sky-900 dark:text-sky-100',
    dot: 'bg-sky-500',
  },
  'female-worker': {
    border: 'border-l-rose-500',
    chip: 'bg-rose-500/12 text-rose-900 dark:text-rose-100',
    dot: 'bg-rose-500',
  },
  'gig-worker': {
    border: 'border-l-orange-500',
    chip: 'bg-orange-500/12 text-orange-900 dark:text-orange-100',
    dot: 'bg-orange-500',
  },
  'labor-dispatch': {
    border: 'border-l-indigo-500',
    chip: 'bg-indigo-500/12 text-indigo-900 dark:text-indigo-100',
    dot: 'bg-indigo-500',
  },
  'work-injury': {
    border: 'border-l-red-600',
    chip: 'bg-red-600/12 text-red-900 dark:text-red-100',
    dot: 'bg-red-600',
  },
};
