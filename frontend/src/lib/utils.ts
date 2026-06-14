import { type ClassValue, clsx } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function resolveImageUrl(filePath: string): string {
  if (filePath.startsWith('http') || filePath.startsWith('/')) return filePath
  return `/static/${filePath}`
}
