import {
  forwardRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from 'react'

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(' ')
}

// ── Spinner ──
export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cx('animate-spin', className)}
      width="1em"
      height="1em"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

// ── Button ──
type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const variants: Record<Variant, string> = {
  primary:
    'bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 shadow-sm disabled:bg-brand-300',
  secondary:
    'bg-surface text-ink border border-border-2 hover:bg-surface-2 active:bg-canvas disabled:text-faint',
  ghost: 'text-brand-700 hover:bg-brand-50 active:bg-brand-100 disabled:text-faint',
  danger: 'bg-error text-white hover:opacity-90 active:opacity-80 disabled:opacity-50',
}
const sizes: Record<Size, string> = {
  sm: 'h-9 px-3.5 text-sm gap-1.5',
  md: 'h-11 px-5 text-[0.95rem] gap-2',
  lg: 'h-13 px-7 text-base gap-2.5',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, icon, disabled, className, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cx(
        'inline-flex items-center justify-center rounded-full font-medium font-sans',
        'transition-[background-color,color,box-shadow,opacity,transform] duration-150',
        'active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100',
        variants[variant],
        sizes[size],
        className,
      )}
      {...rest}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  )
})

// ── Field wrapper ──
interface FieldProps {
  label: string
  htmlFor?: string
  hint?: string
  error?: string
  children: ReactNode
  className?: string
}
export function Field({ label, htmlFor, hint, error, children, className }: FieldProps) {
  return (
    <div className={cx('flex flex-col gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-sm text-error">{error}</p>
      ) : hint ? (
        <p className="text-sm text-muted">{hint}</p>
      ) : null}
    </div>
  )
}

const fieldBase =
  'w-full rounded-lg bg-surface border border-border-2 px-3.5 text-ink placeholder:text-faint ' +
  'transition-[border-color,box-shadow] duration-150 ' +
  'focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-600/30 ' +
  'disabled:bg-surface-2 disabled:text-muted aria-[invalid=true]:border-error'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} className={cx(fieldBase, 'h-11', className)} {...rest} />
  },
)

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...rest }, ref) {
  return <textarea ref={ref} className={cx(fieldBase, 'py-2.5 min-h-24 resize-y', className)} {...rest} />
})

// ── Card ──
export function Card({
  children,
  className,
  as: As = 'div',
}: {
  children: ReactNode
  className?: string
  as?: 'div' | 'section' | 'form' | 'li'
}) {
  return (
    <As className={cx('rounded-xl bg-surface border border-border shadow-sm', className)}>
      {children}
    </As>
  )
}

// ── Chip ──
export function Chip({
  children,
  selected,
  onClick,
  onRemove,
}: {
  children: ReactNode
  selected?: boolean
  onClick?: () => void
  onRemove?: () => void
}) {
  const interactive = !!onClick
  return (
    <span
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick?.()
              }
            }
          : undefined
      }
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium transition-colors',
        interactive && 'cursor-pointer',
        selected
          ? 'bg-olive-500 text-white'
          : 'bg-olive-500/12 text-olive-700 hover:bg-olive-500/20',
      )}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          aria-label="Remove"
          onClick={(e) => {
            e.stopPropagation()
            onRemove()
          }}
          className="-mr-1 grid h-4 w-4 place-items-center rounded-full hover:bg-black/10"
        >
          ×
        </button>
      )}
    </span>
  )
}

// ── Alert ──
export function Alert({
  tone = 'error',
  children,
}: {
  tone?: 'error' | 'success' | 'info'
  children: ReactNode
}) {
  const tones = {
    error: 'bg-error-bg text-error',
    success: 'bg-success-bg text-success',
    info: 'bg-brand-50 text-brand-700',
  }
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={cx('rounded-lg px-3.5 py-2.5 text-sm', tones[tone])}>
      {children}
    </div>
  )
}
