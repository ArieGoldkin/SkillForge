interface ErrorAlertProps {
  message: string
}

export function ErrorAlert({ message }: ErrorAlertProps) {
  return (
    <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
      <p className="text-destructive font-medium">{message}</p>
    </div>
  )
}
