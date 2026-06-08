import { cn } from '@/lib/utils';
import { BRAND } from '@/config/brand';
import { ASSETS } from '@/config/assets';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showWordmark?: boolean;
  className?: string;
  variant?: 'default' | 'inverse';
}

const sizes = {
  sm: { img: 'h-8 w-8', word: 'text-sm', sub: 'hidden' },
  md: { img: 'h-12 w-12', word: 'text-base', sub: 'text-[10px]' },
  lg: { img: 'h-24 w-24', word: 'text-xl', sub: 'text-[11px]' },
};

/** LaborAid 品牌标识 — 浅色背景用原色，深色背景用白色版 */
export default function Logo({
  size = 'md',
  showWordmark = false,
  className,
  variant = 'default',
}: LogoProps) {
  const s = sizes[size];
  const inverse = variant === 'inverse';
  // 浅色背景用原色 Logo，深色背景用白色版
  const logoSrc = inverse ? ASSETS.logoWhite : BRAND.logoUrl;

  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <img
        src={logoSrc}
        alt={`${BRAND.name} ${BRAND.nameEn}`}
        className={cn(s.img, 'shrink-0 object-contain')}
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
