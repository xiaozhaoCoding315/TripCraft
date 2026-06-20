import type { ReactNode } from 'react'

interface Props {
  phase: 'idle' | 'planning' | 'result'
  children: ReactNode
}

export default function ContextPanel({ children }: Props) {
  return <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>{children}</div>
}
