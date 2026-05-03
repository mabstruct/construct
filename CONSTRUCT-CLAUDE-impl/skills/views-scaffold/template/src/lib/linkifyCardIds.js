// Given markdown text, replace backticked tokens that match real card-ids in
// `cardsById` with markdown links pointing at the right workspace's wiki
// anchor. Tokens that don't match a known card-id are left as plain code
// spans — arbitrary `code` and identifiers like `npm` or `useFetch` are
// preserved.
//
// Workspace resolution per token:
//   1. If the matched card object carries `workspace_id` (article source_cards
//      shape), use that. Articles span workspaces, so a card-id in the body
//      may belong to any of them.
//   2. Otherwise fall back to `workspaceFallback` — the surrounding-page
//      workspace (e.g. DigestDetail at /:workspace/digests/:id).
//   3. If neither resolves, leave the token alone (don't fabricate a link).
//
// Used by DigestDetail (top_findings[].summary), ArticleDetail
// (article.body_markdown), and Wiki (card.body_markdown) per
// spec-v02-knowledge-views-spike.md §3.5.
export function linkifyCardIds(markdown, cardsById, workspaceFallback) {
  if (!markdown || !cardsById || cardsById.size === 0) return markdown
  return markdown.replace(/`([a-z0-9][a-z0-9\-]*)`/g, (match, id) => {
    const card = cardsById.get(id)
    if (!card) return match
    const ws = card.workspace_id || workspaceFallback
    if (!ws) return match
    return `[\`${id}\`](/${ws}/wiki#${id})`
  })
}
