/**
 * Download markdown content as a file
 *
 * Uses a delayed cleanup to ensure the browser has time to initiate
 * the download before the object URL is revoked.
 */
export function downloadMarkdown(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()

  // Delay cleanup to ensure download starts before revoking URL
  setTimeout(() => {
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }, 100)
}
