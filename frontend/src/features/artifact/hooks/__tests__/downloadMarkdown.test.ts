/**
 * Tests for downloadMarkdown - Browser file download utility
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { downloadMarkdown } from '../downloadMarkdown'

describe('downloadMarkdown', () => {
  // Store original implementations
  const originalCreateObjectURL = URL.createObjectURL
  const originalRevokeObjectURL = URL.revokeObjectURL

  // Mock functions
  const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
  const mockRevokeObjectURL = vi.fn()
  const mockClick = vi.fn()
  const mockAppendChild = vi.fn()
  const mockRemoveChild = vi.fn()

  beforeEach(() => {
    // Mock URL methods
    URL.createObjectURL = mockCreateObjectURL
    URL.revokeObjectURL = mockRevokeObjectURL

    // Mock document.createElement to return a mock link
    vi.spyOn(document, 'createElement').mockReturnValue({
      href: '',
      download: '',
      click: mockClick,
    } as unknown as HTMLAnchorElement)

    // Mock document.body methods
    vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild)
    vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild)
  })

  afterEach(() => {
    // Restore original implementations
    URL.createObjectURL = originalCreateObjectURL
    URL.revokeObjectURL = originalRevokeObjectURL
    vi.restoreAllMocks()
  })

  it('creates blob with correct content and MIME type', () => {
    const content = '# Test Markdown'
    const filename = 'test.md'

    downloadMarkdown(content, filename)

    expect(mockCreateObjectURL).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'text/markdown',
      })
    )
  })

  it('sets correct href and download attributes on link', () => {
    const mockLink = {
      href: '',
      download: '',
      click: mockClick,
    }
    vi.spyOn(document, 'createElement').mockReturnValue(mockLink as unknown as HTMLAnchorElement)

    downloadMarkdown('content', 'my-file.md')

    expect(mockLink.href).toBe('blob:mock-url')
    expect(mockLink.download).toBe('my-file.md')
  })

  it('appends link to body, clicks it, then removes it', () => {
    downloadMarkdown('content', 'test.md')

    expect(mockAppendChild).toHaveBeenCalled()
    expect(mockClick).toHaveBeenCalled()
    expect(mockRemoveChild).toHaveBeenCalled()
  })

  it('revokes object URL to prevent memory leaks', () => {
    downloadMarkdown('content', 'test.md')

    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
  })
})
