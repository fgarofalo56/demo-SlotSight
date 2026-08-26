import { useState } from 'react'
import { Logo } from './components/Logo'
import { Dashboard } from './pages/Dashboard'
import { Machines } from './pages/Machines'
import { Market } from './pages/Market'
import { Recommendations } from './pages/Recommendations'
import { Ask } from './pages/Ask'

type Tab = 'dashboard' | 'machines' | 'recommendations' | 'market' | 'ask'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '◧' },
  { id: 'machines', label: 'Machines', icon: '▤' },
  { id: 'recommendations', label: 'Recommendations', icon: '◆' },
  { id: 'market', label: 'Market', icon: '◈' },
  { id: 'ask', label: 'Ask SlotSight', icon: '✦' },
]

const WINDOWS = [7, 30, 90]

export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [windowDays, setWindowDays] = useState(30)

  return (
    <div className="min-h-full">
      {/* Every page carries this. The repo is public and the data is invented;
          a viewer must never mistake it for a real property's numbers. */}
      <div className="bg-magenta/12 px-4 py-1.5 text-center text-[0.7rem] tracking-wide text-magenta">
        DEMO — Neon Palms Casino Resort is fictional and every number here is synthetic.
        See NOTICE.md.
      </div>

      <header className="border-b border-gold/15 bg-felt-deep/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <Logo />
            <div>
              <h1 className="font-display text-xl leading-none tracking-wide text-gold np-neon-text">
                SlotSight
              </h1>
              <p className="mt-0.5 text-[0.68rem] uppercase tracking-[0.18em] text-bone-dim">
                Neon Palms Casino Resort
              </p>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <span className="mr-1 text-[0.68rem] uppercase tracking-wider text-bone-dim">
              Window
            </span>
            {WINDOWS.map((d) => (
              <button
                key={d}
                onClick={() => setWindowDays(d)}
                className={`rounded-md border px-2.5 py-1 text-xs transition ${
                  windowDays === d
                    ? 'border-gold/60 bg-gold/20 text-gold'
                    : 'border-bone/15 text-bone-dim hover:bg-bone/10'
                }`}
                aria-pressed={windowDays === d}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        <nav className="mx-auto max-w-7xl px-4" aria-label="Main">
          <ul className="flex flex-wrap gap-1">
            {TABS.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => setTab(t.id)}
                  aria-current={tab === t.id ? 'page' : undefined}
                  className={`flex items-center gap-2 rounded-t-md border-b-2 px-3 py-2 text-sm transition ${
                    tab === t.id
                      ? 'border-gold text-gold'
                      : 'border-transparent text-bone-dim hover:text-bone'
                  }`}
                >
                  <span aria-hidden="true">{t.icon}</span>
                  {t.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        {tab === 'dashboard' && <Dashboard windowDays={windowDays} />}
        {tab === 'machines' && <Machines windowDays={windowDays} />}
        {tab === 'recommendations' && <Recommendations windowDays={windowDays} />}
        {tab === 'market' && <Market />}
        {tab === 'ask' && <Ask windowDays={windowDays} />}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 pt-2 text-center text-[0.68rem] text-bone-dim/60">
        SlotSight · a spec-driven development demo for GitHub Copilot ·{' '}
        <span className="text-bone-dim">analytics are deterministic; the AI only phrases</span>
      </footer>
    </div>
  )
}
