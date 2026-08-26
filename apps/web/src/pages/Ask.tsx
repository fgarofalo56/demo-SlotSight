import { useRef, useState } from 'react'
import { Panel, Spinner } from '../components/ui'
import { ApiError, api } from '../lib/api'
import type { ChatResponse } from '../lib/types'

const SUGGESTIONS = [
  'Which of our penny video slots are underperforming this month?',
  'What should we convert, and to what?',
  'Is the High Limit salon healthy?',
  'Is there anything wrong with the data?',
]

interface Turn {
  question: string
  response?: ChatResponse
  error?: string
  notConfigured?: boolean
}

/** Minimal markdown: **bold**, `code`, and GitHub-style tables. */
function renderAnswer(text: string) {
  const blocks = text.split('\n\n')
  return blocks.map((block, bi) => {
    const lines = block.split('\n')
    const isTable = lines.length > 1 && lines[0]?.includes('|') && lines[1]?.includes('-')

    if (isTable) {
      const rows = lines.filter((l) => l.includes('|'))
      const header = rows[0]?.split('|').map((c) => c.trim()).filter(Boolean) ?? []
      const body = rows.slice(2).map((r) => r.split('|').map((c) => c.trim()).filter(Boolean))
      return (
        <div key={bi} className="my-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gold/25 text-left text-bone-dim">
                {header.map((h, i) => (
                  <th key={i} className="py-1.5 pr-3 font-medium">
                    {h.replace(/\*\*/g, '')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, ri) => (
                <tr key={ri} className="border-b border-bone/5 last:border-0">
                  {row.map((c, ci) => (
                    <td key={ci} className="py-1.5 pr-3 font-mono">
                      {c.replace(/\*\*/g, '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    const html = block
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-gold">$1</strong>')
      .replace(/`(.+?)`/g, '<code class="font-mono text-cyan">$1</code>')
      .replace(/\n/g, '<br/>')

    return (
      <p
        key={bi}
        className="my-2 text-sm leading-relaxed text-bone"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    )
  })
}

export function Ask({ windowDays }: { windowDays: number }) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function submit(question: string) {
    if (!question.trim() || busy) return
    setBusy(true)
    setInput('')
    const idx = turns.length
    setTurns((t) => [...t, { question }])

    try {
      const response = await api.chat(question, windowDays)
      setTurns((t) => t.map((turn, i) => (i === idx ? { ...turn, response } : turn)))
    } catch (err) {
      const apiErr = err as ApiError
      const detail = apiErr.detail as { message?: string } | undefined
      setTurns((t) =>
        t.map((turn, i) =>
          i === idx
            ? {
                ...turn,
                error: detail?.message ?? apiErr.message,
                notConfigured: apiErr.isNotConfigured,
              }
            : turn,
        ),
      )
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        title="Ask SlotSight"
        subtitle="Every answer is produced by the same deterministic analytics the dashboard uses. The model phrases; the SQL decides."
      >
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => submit(s)}
              disabled={busy}
              className="rounded-md border border-cyan/25 bg-cyan/5 px-3 py-1.5 text-left text-xs text-cyan transition hover:bg-cyan/15 disabled:opacity-40"
            >
              {s}
            </button>
          ))}
        </div>
      </Panel>

      {turns.map((turn, i) => (
        <div key={i} className="space-y-2">
          <div className="np-panel border-cyan/25 p-3">
            <p className="text-sm text-cyan">{turn.question}</p>
          </div>

          {!turn.response && !turn.error && <Spinner label="Querying the floor" />}

          {turn.error && (
            <div className="np-panel border-magenta/40 p-4">
              <h3 className="font-display text-magenta">
                {turn.notConfigured ? 'Azure OpenAI is not configured' : 'That request failed'}
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-bone-dim">{turn.error}</p>
              {turn.notConfigured && (
                <p className="mt-2 text-xs text-bone-dim">
                  The dashboard, machines, and recommendations pages do not need Azure OpenAI and
                  are working normally — only this conversational feature requires it.
                </p>
              )}
            </div>
          )}

          {turn.response && (
            <div className="np-panel p-4">
              {renderAnswer(turn.response.answer)}

              {turn.response.tool_calls.length > 0 && (
                <details className="mt-4 border-t border-bone/10 pt-3">
                  <summary className="cursor-pointer text-xs text-bone-dim hover:text-cyan">
                    {turn.response.tool_calls.length} analytics call
                    {turn.response.tool_calls.length === 1 ? '' : 's'} produced this answer —
                    every number is reproducible
                  </summary>
                  <ul className="mt-2 space-y-1.5">
                    {turn.response.tool_calls.map((c, ci) => (
                      <li key={ci} className="font-mono text-[0.68rem] text-bone-dim">
                        <span className="text-gold">{c.tool}</span>
                        <span className="text-bone-dim/60">
                          ({JSON.stringify(c.arguments)})
                        </span>
                        <div className="pl-4 text-cyan/70">→ {c.result_summary}</div>
                      </li>
                    ))}
                  </ul>
                </details>
              )}

              {!turn.response.grounded && (
                <p className="mt-3 rounded bg-amber-500/10 p-2 text-xs text-amber-400">
                  ⚠ This answer was produced without an analytics call, so it is not grounded in
                  floor data. Treat it with suspicion.
                </p>
              )}
            </div>
          )}
        </div>
      ))}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit(input)
        }}
        className="np-panel flex gap-2 p-3"
      >
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          placeholder="Ask about the floor…"
          aria-label="Ask a question about the slot floor"
          className="flex-1 bg-transparent px-2 py-1.5 text-sm text-bone placeholder:text-bone-dim/60 focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-md border border-gold/40 bg-gold/15 px-4 py-1.5 text-sm text-gold transition hover:bg-gold/25 disabled:opacity-40"
        >
          {busy ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
