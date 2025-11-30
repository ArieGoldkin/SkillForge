import {
  CodeRenderer,
  InputRenderer,
  ListItemRenderer,
  TableRenderer,
  UnorderedListRenderer,
} from './internal'

/**
 * Combined renderers object for ReactMarkdown components prop
 */
export const markdownRenderers = {
  code: CodeRenderer,
  table: TableRenderer,
  input: InputRenderer,
  li: ListItemRenderer,
  ul: UnorderedListRenderer,
}
