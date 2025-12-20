/**
 * Tests for downloadMarkdown - Browser file download utility
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createMockAnchorElement } from '@/test-utils/factories'

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
    // Use fake timers for setTimeout in downloadMarkdown
    vi.useFakeTimers()

    // Clear all mocks before each test
    mockCreateObjectURL.mockClear()
    mockRevokeObjectURL.mockClear()
    mockClick.mockClear()
    mockAppendChild.mockClear()
    mockRemoveChild.mockClear()

    // Mock URL methods
    URL.createObjectURL = mockCreateObjectURL
    URL.revokeObjectURL = mockRevokeObjectURL

    // Mock document.createElement to return a mock link
    vi.spyOn(document, 'createElement').mockReturnValue(
      createMockAnchorElement({
        href: '',
        download: '',
        click: mockClick,
      })
    )

    // Mock document.body methods
    vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild)
    vi.spyOn(document.body, 'removeChild').mockImplementation(mockRemoveChild)
  })

  afterEach(() => {
    // Restore original implementations
    URL.createObjectURL = originalCreateObjectURL
    URL.revokeObjectURL = originalRevokeObjectURL
    vi.useRealTimers()
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
    const mockLink = createMockAnchorElement({
      href: '',
      download: '',
      click: mockClick,
    })
    vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

    downloadMarkdown('content', 'my-file.md')

    expect(mockLink.href).toBe('blob:mock-url')
    expect(mockLink.download).toBe('my-file.md')
  })

  it('appends link to body, clicks it, then removes it after delay', () => {
    downloadMarkdown('content', 'test.md')

    // Immediate actions
    expect(mockAppendChild).toHaveBeenCalled()
    expect(mockClick).toHaveBeenCalled()

    // Cleanup happens after 100ms delay
    expect(mockRemoveChild).not.toHaveBeenCalled()
    vi.advanceTimersByTime(100)
    expect(mockRemoveChild).toHaveBeenCalled()
  })

  it('revokes object URL after delay to prevent memory leaks', () => {
    downloadMarkdown('content', 'test.md')

    // URL is not revoked immediately (allows download to start)
    expect(mockRevokeObjectURL).not.toHaveBeenCalled()

    // After delay, URL is revoked
    vi.advanceTimersByTime(100)
    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
  })
})
