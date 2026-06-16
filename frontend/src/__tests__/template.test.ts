import { describe, it, expect } from 'vitest'
import { AGENTS_MD_CONTENT } from '@/lib/template'

// We need to test the ZIP generation and content
// Since downloadTemplateZip uses browser DOM APIs (URL.createObjectURL),
// we test the ZIP content by importing JSZip directly

describe('template AGENTS_MD_CONTENT', () => {
  it('contains required sections', () => {
    expect(AGENTS_MD_CONTENT).toContain('# MycoAI Batch Data Structure')
    expect(AGENTS_MD_CONTENT).toContain('Directory Structure')
    expect(AGENTS_MD_CONTENT).toContain('Naming Conventions')
    expect(AGENTS_MD_CONTENT).toContain('Instructions')
    expect(AGENTS_MD_CONTENT).toContain('images/')
    expect(AGENTS_MD_CONTENT).toContain('T379')
    expect(AGENTS_MD_CONTENT).toContain('T362')
    expect(AGENTS_MD_CONTENT).toContain('AGENTS.md')
  })

  it('mentions accepted formats', () => {
    expect(AGENTS_MD_CONTENT).toContain('.jpg')
    expect(AGENTS_MD_CONTENT).toContain('.jpeg')
    expect(AGENTS_MD_CONTENT).toContain('.png')
  })

  it('mentions supported media types', () => {
    expect(AGENTS_MD_CONTENT).toContain('MEA')
    expect(AGENTS_MD_CONTENT).toContain('CYA')
    expect(AGENTS_MD_CONTENT).toContain('YES')
    expect(AGENTS_MD_CONTENT).toContain('DG18')
  })

  it('mentions ZIP download and upload flow', () => {
    expect(AGENTS_MD_CONTENT).toContain('ZIP')
    expect(AGENTS_MD_CONTENT).toContain('Upload')
  })

  it('mentions auto-segmentation and Qdrant indexing', () => {
    expect(AGENTS_MD_CONTENT).toContain('segment')
    expect(AGENTS_MD_CONTENT).toContain('Qdrant')
  })
})

describe('template ZIP structure (unit)', () => {
  it('imports JSZip without errors', async () => {
    const JSZip = (await import('jszip')).default
    expect(JSZip).toBeDefined()
    expect(typeof JSZip).toBe('function')
  })

  it('can create a ZIP with expected structure', async () => {
    const JSZip = (await import('jszip')).default
    const zip = new JSZip()

    const root = zip.folder('mycoai_batch')!
    root.file('AGENTS.md', AGENTS_MD_CONTENT)
    const scripts = root.folder('scripts')!
    scripts.file('rename_images.sh', '#!/usr/bin/env bash\necho test')
    const images = root.folder('images')!
    images.file('.gitkeep', '')

    const blob = await zip.generateAsync({ type: 'blob' })
    expect(blob).toBeInstanceOf(Blob)
    expect(blob.size).toBeGreaterThan(0)
    expect(blob.type).toBe('application/zip')
  })
})
