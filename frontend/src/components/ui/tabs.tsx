import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function Tabs({ defaultValue, children, className, ...props }: HTMLAttributes<HTMLDivElement> & { defaultValue: string }) {
  return (
    <div className={cn('w-full', className)} data-default-value={defaultValue} {...props}>
      {children}
    </div>
  )
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground', className)} {...props} />
  )
}

export function TabsTrigger({ value, active, className, ...props }: HTMLAttributes<HTMLButtonElement> & { value: string; active?: boolean }) {
  return (
    <button
      data-value={value}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        active && 'bg-card text-foreground shadow-sm',
        !active && 'hover:bg-card/50',
        className,
      )}
      {...props}
    />
  )
}

export function TabsContent({ value, activeValue, className, ...props }: HTMLAttributes<HTMLDivElement> & { value: string; activeValue: string }) {
  if (value !== activeValue) return null
  return <div className={cn('mt-4', className)} {...props} />
}
