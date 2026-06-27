import { useState } from 'react'
import { motion, useReducedMotion, type TargetAndTransition } from 'motion/react'

export type Mood = 'idle' | 'think' | 'cheer' | 'wave' | 'sad' | 'peek'

const DEFAULT_SRC = '/zatoona.png'
// Flip to true once per-mood art exists in public/mascot/ (see that folder's README).
const USE_MOOD_ART = false

const moods: Record<Mood, TargetAndTransition> = {
  idle: { y: [0, -8, 0], rotate: [-1.5, 1.5, -1.5] },
  think: { rotate: [-3, 3, -3], y: [0, -4, 0] },
  cheer: { y: [0, -18, 0], scale: [1, 1.04, 1] },
  wave: { rotate: [-5, 5, -5] },
  sad: { y: [0, 4, 0], rotate: [-1, 0, -1] },
  peek: { y: [10, 0, 10] },
}

const timing: Record<Mood, number> = {
  idle: 4,
  think: 2.6,
  cheer: 0.75,
  wave: 1.3,
  sad: 3.2,
  peek: 3.5,
}

interface Props {
  mood?: Mood
  size?: number
  className?: string
  /** decorative by default; pass a label to make it meaningful to AT */
  label?: string
}

export function Mascot({ mood = 'idle', size = 140, className, label }: Props) {
  const reduce = useReducedMotion()
  const [src, setSrc] = useState(USE_MOOD_ART ? `/mascot/${mood}.png` : DEFAULT_SRC)
  return (
    <motion.img
      src={src}
      onError={() => src !== DEFAULT_SRC && setSrc(DEFAULT_SRC)}
      alt={label ?? ''}
      aria-hidden={label ? undefined : true}
      width={size}
      height={size}
      draggable={false}
      className={className}
      style={{ width: size, height: size, willChange: 'transform' }}
      animate={reduce ? undefined : moods[mood]}
      transition={
        reduce
          ? undefined
          : { duration: timing[mood], repeat: Infinity, ease: 'easeInOut' }
      }
    />
  )
}
