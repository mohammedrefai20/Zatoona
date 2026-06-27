import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { useAuth } from '../lib/auth'
import { ApiError, ingestEnrichment, listEnrichment, proposeEnrichment, removeEnrichment } from '../lib/api'
import type { EnrichItem, Proposal } from '../lib/types'
import { Mascot } from './Mascot'
import { Alert, Button, Card, Chip, Spinner, cx } from './ui'

export function EnrichPanel({ hasTopics }: { hasTopics: boolean }) {
  const { withAuth } = useAuth()
  const [enriched, setEnriched] = useState<EnrichItem[] | null>(null)
  const [proposals, setProposals] = useState<Proposal[] | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [proposing, setProposing] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const refreshList = useCallback(() => {
    withAuth((t) => listEnrichment(t))
      .then((r) => setEnriched(r.items))
      .catch(() => setEnriched([]))
  }, [withAuth])

  useEffect(() => refreshList(), [refreshList])

  async function onPropose() {
    setError('')
    setMessage('')
    setProposing(true)
    try {
      const r = await withAuth((t) => proposeEnrichment(t))
      setProposals(r.proposals)
      setSelected(new Set(r.proposals.map((p) => p.url))) // default: all selected
      if (r.proposals.length === 0) setMessage('No new suggestions found for your topics.')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Web search failed. Try again.')
    } finally {
      setProposing(false)
    }
  }

  async function onIngest() {
    if (!proposals) return
    const chosen = proposals.filter((p) => selected.has(p.url))
    if (chosen.length === 0) return setError('Select at least one page to add.')
    setError('')
    setMessage('')
    setIngesting(true)
    try {
      const r = await withAuth((t) => ingestEnrichment(t, chosen))
      const added = r.outcomes.filter((o) => o.status === 'ingested').length
      const skipped = r.outcomes.length - added
      setMessage(`Added ${added} page${added === 1 ? '' : 's'}${skipped ? `, skipped ${skipped}` : ''}.`)
      setProposals(null)
      setSelected(new Set())
      refreshList()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not add pages. Try again.')
    } finally {
      setIngesting(false)
    }
  }

  async function onRemoveAll() {
    setError('')
    try {
      await withAuth((t) => removeEnrichment(t))
      setMessage('Removed all web sources.')
      refreshList()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not remove web sources.')
    }
  }

  function toggle(url: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(url)) next.delete(url)
      else next.add(url)
      return next
    })
  }

  const busy = proposing || ingesting

  return (
    <Card className="mt-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-brand-800">
            <span aria-hidden>✨</span> Enrich from the web
            <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs font-medium text-muted">optional</span>
          </h2>
          <p className="mt-1 max-w-prose text-sm text-muted">
            Pull in a few relevant web pages to round out your material. Suggestions come from the topics
            you've already uploaded — you choose what gets added, and you can remove it any time.
          </p>
        </div>
        {!busy && (
          <Button variant="secondary" size="sm" onClick={onPropose} disabled={!hasTopics}>
            {proposals ? 'Search again' : 'Suggest pages'}
          </Button>
        )}
      </div>

      {!hasTopics && (
        <p className="mt-4 rounded-lg bg-surface-2 px-3.5 py-2.5 text-sm text-muted">
          Add some notes first — suggestions are based on your topics.
        </p>
      )}

      {busy && (
        <div className="mt-5 flex items-center gap-3 rounded-lg bg-brand-50 px-4 py-3">
          <Mascot mood="think" size={40} />
          <p className="text-sm font-medium text-brand-800">
            {proposing ? 'Searching the web for relevant pages…' : 'Fetching & adding the pages you picked…'}
          </p>
          <Spinner className="ml-auto text-brand-500" />
        </div>
      )}

      {error && <div className="mt-4"><Alert tone="error">{error}</Alert></div>}
      {message && !busy && <div className="mt-4"><Alert tone="success">{message}</Alert></div>}

      {/* Proposals to review */}
      <AnimatePresence>
        {proposals && proposals.length > 0 && !busy && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <ul className="mt-5 flex flex-col gap-2">
              {proposals.map((p) => (
                <li key={p.url}>
                  <label
                    className={cx(
                      'flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors',
                      selected.has(p.url) ? 'border-brand-300 bg-brand-50/60' : 'border-border hover:bg-surface-2',
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(p.url)}
                      onChange={() => toggle(p.url)}
                      className="mt-1 h-4 w-4 accent-[var(--color-brand-600)]"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate font-medium text-ink">{p.title}</span>
                        <Chip>{p.topic}</Chip>
                      </span>
                      {p.snippet && <span className="mt-0.5 line-clamp-2 block text-sm text-muted">{p.snippet}</span>}
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="mt-1 block truncate text-xs text-brand-600 hover:underline"
                      >
                        {p.url}
                      </a>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex items-center gap-3">
              <Button onClick={onIngest} disabled={selected.size === 0}>
                Add {selected.size} selected
              </Button>
              <button onClick={() => setProposals(null)} className="text-sm font-medium text-muted hover:text-ink">
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Already-added web sources */}
      {enriched && enriched.length > 0 && (
        <div className="mt-6 border-t border-border pt-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-ink">From the web ({enriched.length})</p>
            <button onClick={onRemoveAll} className="text-sm font-medium text-error hover:underline">
              Remove all
            </button>
          </div>
          <ul className="mt-2.5 flex flex-col gap-1.5">
            {enriched.slice(0, 8).map((it) => (
              <li key={it.chunk_id} className="flex items-center gap-2 text-sm">
                <span className="text-olive-600" aria-hidden>
                  🌐
                </span>
                <a
                  href={it.url ?? '#'}
                  target="_blank"
                  rel="noreferrer"
                  className="truncate text-ink hover:underline"
                >
                  {it.title || it.url}
                </a>
                {it.topic && <Chip>{it.topic}</Chip>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  )
}
