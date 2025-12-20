/** ArtifactPreviewModal - Modal for previewing implementation guide before download */

import { FileText, Link as LinkIcon } from 'lucide-react'

import { Button } from '@shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@shared/components/ui/dialog'

import { ModalContent } from './internal'
import type { ArtifactPreviewModalProps } from './types'

export function ArtifactPreviewModal(props: ArtifactPreviewModalProps) {
  const { isOpen, onClose, content, isLoading, error, onDownload, sourceUrl, artifactId } = props

  const handleDownload = () => {
    onDownload?.()
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open: boolean) => !open && onClose()}>
      <DialogContent className="flex max-h-[90vh] w-full max-w-4xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b border-border px-6 py-4">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5 text-primary" />
            Implementation Guide Preview
          </DialogTitle>
          {sourceUrl && (
            <DialogDescription className="flex items-center gap-1.5 text-sm">
              <LinkIcon className="h-3.5 w-3.5" />
              <span className="truncate">{sourceUrl}</span>
            </DialogDescription>
          )}
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ModalContent
            content={content}
            isLoading={isLoading}
            error={error}
            artifactId={artifactId}
          />
        </div>
        <DialogFooter className="shrink-0 border-t border-border bg-muted/50 px-6 py-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={handleDownload} disabled={!content || isLoading}>
            Download Guide
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export type { ArtifactPreviewModalProps } from './types'
