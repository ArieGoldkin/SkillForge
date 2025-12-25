/**
 * ActionCardHeader - Header for AnalysisActionsCard
 */

import type { AnalysisStatus } from '@app-types/api'
import { AlertCircle, AlertTriangle } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { CardDescription, CardHeader, CardTitle } from '@shared/components/ui/card'

import { getCardDescription, getStatusLabel } from './helpers'

export interface ActionCardHeaderProps {
  status: AnalysisStatus
  isFailed: boolean
}

export function ActionCardHeader({ status, isFailed }: ActionCardHeaderProps) {
  return (
    <CardHeader>
      <div className="flex items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          {isFailed ? (
            <>
              <AlertTriangle className="h-5 w-5 text-destructive" />
              {getStatusLabel(status)}
            </>
          ) : (
            <>
              <AlertCircle className="h-5 w-5 text-primary" />
              Rerun Analysis
            </>
          )}
        </CardTitle>
        <Badge variant={isFailed ? 'destructive' : 'secondary'}>{status}</Badge>
      </div>
      <CardDescription>{getCardDescription(isFailed)}</CardDescription>
    </CardHeader>
  )
}
