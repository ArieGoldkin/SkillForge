import {
  CodeRenderer,
  H1Renderer,
  H2Renderer,
  H3Renderer,
  H4Renderer,
  H5Renderer,
  H6Renderer,
  InputRenderer,
  ListItemRenderer,
  ParagraphRenderer,
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
  p: ParagraphRenderer,
  h1: H1Renderer,
  h2: H2Renderer,
  h3: H3Renderer,
  h4: H4Renderer,
  h5: H5Renderer,
  h6: H6Renderer,
}
