import { cn } from '@/lib/utils';
import { BRAND } from '@/config/brand';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showWordmark?: boolean;
  className?: string;
  variant?: 'default' | 'inverse';
}

const sizes = {
  sm: { img: 'h-8 w-8', word: 'text-sm', sub: 'hidden' },
  md: { img: 'h-10 w-10', word: 'text-base', sub: 'text-[10px]' },
  lg: { img: 'h-16 w-16', word: 'text-xl', sub: 'text-[11px]' },
};

/** LaborAid 品牌标识 */
export default function Logo({
  size = 'md',
  showWordmark = true,
  className,
  variant = 'default',
}: LogoProps) {
  const s = sizes[size];
  const inverse = variant === 'inverse';

  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <img
        src={BRAND.logoUrl}
        alt={`${BRAND.name} ${BRAND.nameEn}`}
        className={cn(s.img, 'shrink-0 rounded-full object-cover ring-1 ring-border/40 bg-white')}
      />
      {showWordmark && (
        <div className="min-w-0 leading-tight">
          <span
            className={cn(
              'block font-display font-semibold tracking-tight',
              s.word,
              inverse ? 'text-white' : 'text-foreground',
            )}
          >
            {BRAND.name}
          </span>
          {size !== 'sm' && (
            <span
              className={cn(
                'block font-medium tracking-wide',
                s.sub,
                inverse ? 'text-white/60' : 'text-muted-foreground',
              )}
            >
              {BRAND.nameEn}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
