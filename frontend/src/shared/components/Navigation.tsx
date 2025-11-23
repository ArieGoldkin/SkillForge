import { NavigationActions } from './NavigationActions'
import { NavigationLinks } from './NavigationLinks'

export function Navigation() {
  return (
    <nav className="border-b border-border bg-background">
      <div className="mx-auto max-w-7xl px-8 py-6">
        <div className="flex items-center justify-between">
          <NavigationLinks />
          <NavigationActions />
        </div>
      </div>
    </nav>
  )
}
