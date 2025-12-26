import { useFocusReturn } from '@/hooks'

import { Button } from '@shared/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@shared/components/ui/dialog'

interface ExitSessionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  isPending: boolean
}

export function ExitSessionDialog({
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: ExitSessionDialogProps) {
  // WCAG 2.1 AA: Return focus to trigger element when modal closes
  useFocusReturn(open)
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Exit Tutoring Session?</DialogTitle>
          <DialogDescription>
            Are you sure you want to end this tutoring session? Your progress will be saved and you
            can resume learning later from the artifact page.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            data-testid="cancel-exit-button"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isPending}
            data-testid="confirm-exit-button"
          >
            {isPending ? 'Ending...' : 'End Session'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
