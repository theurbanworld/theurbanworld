/**
 * Build a table-of-contents tree from one or more rendered content bodies.
 *
 * @nuxt/content stores rendered markdown as a "minimark" tree — an array of
 * `[tag, props, ...children]` tuples (text nodes are plain strings). Every
 * heading carries an `id` prop (e.g. `["h2", { id: "source-data" }, "Source data"]`),
 * which doubles as its in-page anchor.
 *
 * We collect h1–h3 headings and nest them by depth so that multi-section pages
 * (where each section's `<h1>` acts as a group header) render as headers with
 * indented subheaders. Pass several bodies to merge them into a single TOC.
 */

type MinimarkNode = string | [string, Record<string, unknown>, ...MinimarkNode[]]

interface MinimarkBody {
  value?: MinimarkNode[]
}

export interface TocItem {
  id: string
  text: string
  depth: number
  children: TocItem[]
}

function nodeText(node: MinimarkNode): string {
  if (typeof node === 'string') return node
  const [, , ...children] = node
  return children.map(nodeText).join('')
}

function collectHeadings(
  nodes: MinimarkNode[] = [],
  out: Array<{ id: string, text: string, depth: number }> = []
) {
  for (const node of nodes) {
    if (typeof node === 'string') continue
    const [tag, props, ...children] = node
    const match = /^h([1-4])$/.exec(tag)
    if (match && typeof props?.id === 'string') {
      out.push({ id: props.id, text: nodeText(node).trim(), depth: Number(match[1]) })
    }
    collectHeadings(children, out)
  }
  return out
}

/**
 * Return a copy of a rendered content body with every heading demoted by `by`
 * levels (h1→h2, h2→h3, …, capped at h6).
 *
 * Content files are authored as standalone documents — each leads with a single
 * `<h1>`, which is correct when the file is shown on its own (e.g. in a modal).
 * When several are concatenated onto one page, those `<h1>`s collide, so the
 * aggregating page demotes them and supplies its own single page-level `<h1>`.
 */
export function shiftHeadings<T extends MinimarkBody | null | undefined>(body: T, by = 1): T {
  if (!body?.value) return body
  return { ...body, value: body.value.map(node => shiftNode(node, by)) }
}

function shiftNode(node: MinimarkNode, by: number): MinimarkNode {
  if (typeof node === 'string') return node
  const [tag, props, ...children] = node
  const match = /^h([1-6])$/.exec(tag)
  const nextTag = match ? `h${Math.min(6, Number(match[1]) + by)}` : tag
  return [nextTag, props, ...children.map(child => shiftNode(child, by))]
}

/**
 * Return a copy of a rendered content body with every heading `id` namespaced
 * by `prefix`.
 *
 * Heading ids are slugified from heading text, and the slug counter resets per
 * file. Concatenating several files onto one page therefore produces duplicate
 * ids (multiple "Temporal coverage" headings all become `#temporal-coverage`),
 * which breaks anchor links and the scrollspy. Prefixing each section's ids with
 * a per-section namespace makes them unique again.
 */
export function prefixHeadingIds<T extends MinimarkBody | null | undefined>(body: T, prefix: string): T {
  if (!body?.value) return body
  const safePrefix = prefix.replace(/[^a-z0-9]+/gi, '-').replace(/(^-|-$)/g, '').toLowerCase()
  if (!safePrefix) return body
  return { ...body, value: body.value.map(node => prefixNode(node, safePrefix)) }
}

function prefixNode(node: MinimarkNode, prefix: string): MinimarkNode {
  if (typeof node === 'string') return node
  const [tag, props, ...children] = node
  const isHeading = /^h[1-6]$/.test(tag)
  const nextProps = isHeading && typeof props?.id === 'string'
    ? { ...props, id: `${prefix}-${props.id}` }
    : props
  return [tag, nextProps, ...children.map(child => prefixNode(child, prefix))]
}

export function buildToc(...bodies: Array<MinimarkBody | null | undefined>): TocItem[] {
  const flat = bodies.flatMap(body => collectHeadings(body?.value))

  const root: TocItem[] = []
  const stack: TocItem[] = []

  for (const heading of flat) {
    const item: TocItem = { ...heading, children: [] }
    while (stack.length && stack[stack.length - 1]!.depth >= heading.depth) stack.pop()
    if (stack.length) stack[stack.length - 1]!.children.push(item)
    else root.push(item)
    stack.push(item)
  }

  return root
}
