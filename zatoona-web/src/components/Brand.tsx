import { cx } from './ui'

interface Props {
  size?: number
  /** white text for dark/drenched surfaces */
  light?: boolean
  className?: string
  tagline?: boolean
}

export function Wordmark({ size = 32, light, className, tagline }: Props) {
  return (
    <span className={cx('inline-flex items-center gap-2.5', className)}>
      <img src="/zatoona.png" alt="" aria-hidden width={size} height={size} style={{ width: size, height: size }} />
      <span className="flex flex-col leading-none">
        <span
          className={cx('font-display font-semibold tracking-tight', light ? 'text-white' : 'text-brand-800')}
          style={{ fontSize: size * 0.62 }}
        >
          Zatoona
        </span>
        {tagline && (
          <span className={cx('mt-1 text-xs font-medium', light ? 'text-brand-200' : 'text-muted')}>
            Study smart
          </span>
        )}
      </span>
    </span>
  )
}
