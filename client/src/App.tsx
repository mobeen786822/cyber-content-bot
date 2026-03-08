import { useState, useEffect, useCallback } from 'react'
import {
  getStatus,
  getDraft,
  triggerRun,
  regenerateDraft,
  type StatusResponse,
  type DraftResponse,
} from './api'

function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [draftData, setDraftData] = useState<DraftResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [tone, setTone] = useState('professional')
  const [copied, setCopied] = useState(false)
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({})

  const fetchAll = useCallback(async () => {
    try {
      const [s, d] = await Promise.all([getStatus(), getDraft()])
      setStatus(s)
      setDraftData(d)
    } catch (e) {
      console.error('Failed to fetch data:', e)
    }
  }, [])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // Poll while loading
  useEffect(() => {
    if (!loading) return
    const interval = setInterval(async () => {
      try {
        const s = await getStatus()
        setStatus(s)
        if (!s.cycle_running) {
          const d = await getDraft()
          setDraftData(d)
          setLoading(false)
        }
      } catch (e) {
        console.error('Poll error:', e)
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [loading])

  const handleRun = async () => {
    setLoading(true)
    try {
      await triggerRun()
    } catch (e) {
      console.error('Run failed:', e)
      setLoading(false)
    }
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      const result = await regenerateDraft(tone)
      setDraftData((prev) =>
        prev ? { ...prev, draft: result.draft } : prev
      )
    } catch (e) {
      console.error('Regenerate failed:', e)
    } finally {
      setRegenerating(false)
    }
  }

  const handleCopy = async () => {
    if (draftData?.draft) {
      await navigator.clipboard.writeText(draftData.draft)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const toggleSource = (key: string) => {
    setExpandedSources((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const formatTime = (iso: string | null) => {
    if (!iso) return 'Never'
    return new Date(iso).toLocaleString()
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-slate-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-16 -top-16 h-64 w-64 rounded-full bg-emerald-500/15 blur-3xl" />
        <div className="absolute right-0 top-0 h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-cyan-900/30 blur-3xl" />
      </div>

      <header className="relative border-b border-cyan-900/40 bg-slate-950/70 px-6 py-5 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl font-semibold tracking-tight text-cyan-100">
              <span className="text-cyan-300">Cyber</span> Content Bot
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Last run: {formatTime(status?.last_run ?? null)}
            </p>
          </div>
          <button
            onClick={handleRun}
            disabled={loading}
            className="inline-flex items-center rounded-full border border-cyan-300/50 bg-cyan-300/90 px-5 py-2.5 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-600/20 transition hover:-translate-y-0.5 hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <Spinner /> Running...
              </span>
            ) : (
              'Run Now'
            )}
          </button>
        </div>
      </header>

      <main className="relative mx-auto max-w-5xl space-y-6 p-6">
        <div className="grid gap-3 rounded-2xl border border-cyan-900/60 bg-slate-900/70 p-4 text-sm backdrop-blur-sm sm:grid-cols-2">
          <StatusPill
            label="Status"
            value={status?.cycle_running ? 'Running' : 'Idle'}
            active={status?.cycle_running ?? false}
          />
          <StatusPill
            label="Findings"
            value={String(status?.num_findings ?? 0)}
          />
        </div>

        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-2xl border border-cyan-900/60 bg-slate-900/70 p-12 backdrop-blur-sm">
            <Spinner />
            <span className="text-slate-300">
              Fetching sources and generating draft... this may take 10-15 seconds
            </span>
          </div>
        )}

        {draftData?.draft && !loading && (
          <div className="overflow-hidden rounded-3xl border border-cyan-900/60 bg-gradient-to-r from-slate-950 via-slate-900 to-cyan-950/40 shadow-soft">
            <div className="flex items-center justify-between border-b border-cyan-900/50 px-5 py-4">
              <h2 className="font-heading text-lg font-semibold">LinkedIn Draft</h2>
              <button
                onClick={handleCopy}
                className="rounded-full border border-cyan-700/60 bg-slate-900/40 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-cyan-300/60 hover:text-cyan-200"
              >
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
            </div>
            <div className="p-5">
              <p className="whitespace-pre-wrap leading-relaxed text-slate-100">
                {draftData.draft}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 border-t border-cyan-900/50 px-5 py-4">
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="appearance-none rounded-full border border-cyan-900/80 bg-slate-950 py-1.5 pl-4 pr-9 text-sm text-slate-200 outline-none transition focus:border-cyan-300"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.75rem center' }}
              >
                <option value="professional" className="bg-slate-950 text-slate-200">Professional</option>
                <option value="conversational" className="bg-slate-950 text-slate-200">Conversational</option>
                <option value="technical" className="bg-slate-950 text-slate-200">Technical</option>
              </select>
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="rounded-full border border-cyan-300/60 px-4 py-1.5 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/15 disabled:opacity-50"
              >
                {regenerating ? 'Regenerating...' : 'Regenerate'}
              </button>
            </div>
          </div>
        )}

        {!draftData?.draft && !loading && (
          <div className="rounded-2xl border border-cyan-900/60 bg-slate-900/70 p-12 text-center backdrop-blur-sm">
            <p className="text-slate-300">
              No draft yet. Click <span className="text-cyan-300">Run Now</span> to
              fetch sources and generate a LinkedIn post.
            </p>
          </div>
        )}

        {draftData && hasFindings(draftData) && !loading && (
          <div className="space-y-3">
            <h2 className="font-heading text-sm font-semibold uppercase tracking-[0.18em] text-cyan-300">
              Sources
            </h2>

            <SourceSection
              title={`NVD CVEs (${draftData.findings.nvd.length})`}
              expanded={expandedSources['nvd'] ?? false}
              onToggle={() => toggleSource('nvd')}
            >
              {draftData.findings.nvd.map((cve) => (
                <div
                  key={cve.cve_id}
                  className="border-b border-cyan-900/40 px-5 py-3 last:border-0"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-cyan-300">
                      {cve.cve_id}
                    </span>
                    <SeverityBadge score={cve.cvss_score} severity={cve.severity} />
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-300">
                    {cve.description}
                  </p>
                  {cve.affected_products.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {cve.affected_products.map((p) => (
                        <span
                          key={p}
                          className="rounded-full border border-cyan-900/50 bg-slate-950 px-2 py-0.5 text-xs text-slate-400"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </SourceSection>

            <SourceSection
              title={`CISA KEV (${draftData.findings.cisa.length})`}
              expanded={expandedSources['cisa'] ?? false}
              onToggle={() => toggleSource('cisa')}
            >
              {draftData.findings.cisa.map((adv) => (
                <div
                  key={adv.cve_id}
                  className="border-b border-cyan-900/40 px-5 py-3 last:border-0"
                >
                  <div className="font-mono text-sm text-cyan-300">
                    {adv.cve_id}
                  </div>
                  <p className="mt-1 text-sm font-medium">{adv.vulnerability_name}</p>
                  <p className="text-sm text-slate-300">
                    {adv.vendor_project} - {adv.product}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Action: {adv.required_action}
                  </p>
                </div>
              ))}
            </SourceSection>

            <SourceSection
              title={`arXiv Papers (${draftData.findings.arxiv.length})`}
              expanded={expandedSources['arxiv'] ?? false}
              onToggle={() => toggleSource('arxiv')}
            >
              {draftData.findings.arxiv.map((paper) => (
                <div
                  key={paper.link}
                  className="border-b border-cyan-900/40 px-5 py-3 last:border-0"
                >
                  <a
                    href={paper.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-cyan-200 transition hover:text-emerald-300"
                  >
                    {paper.title}
                  </a>
                  <p className="mt-1 text-xs text-slate-400">
                    {paper.authors.join(', ')}
                  </p>
                  <p className="mt-1 line-clamp-3 text-sm text-slate-300">
                    {paper.summary}
                  </p>
                </div>
              ))}
            </SourceSection>
          </div>
        )}
      </main>
    </div>
  )
}

function hasFindings(data: DraftResponse): boolean {
  return (
    data.findings.nvd.length > 0 ||
    data.findings.cisa.length > 0 ||
    data.findings.arxiv.length > 0
  )
}

function StatusPill({
  label,
  value,
  active,
}: {
  label: string
  value: string
  active?: boolean
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-cyan-900/50 bg-slate-950/40 px-3 py-2">
      {active !== undefined && (
        <span
          className={`h-2.5 w-2.5 rounded-full ${active ? 'bg-emerald-300' : 'bg-slate-500'}`}
        />
      )}
      <span className="text-slate-400">{label}:</span>
      <span className="text-slate-200">{value}</span>
    </div>
  )
}

function SeverityBadge({ score, severity }: { score: number; severity: string }) {
  const color =
    severity === 'CRITICAL'
      ? 'border-red-400/40 bg-red-900/40 text-red-300'
      : 'border-amber-400/40 bg-amber-900/40 text-amber-300'
  return (
    <span className={`rounded-full border px-1.5 py-0.5 text-xs font-medium ${color}`}>
      {severity} {score}
    </span>
  )
}

function SourceSection({
  title,
  expanded,
  onToggle,
  children,
}: {
  title: string
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-cyan-900/60 bg-slate-900/70 backdrop-blur-sm">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-3 text-left text-sm font-medium transition hover:bg-slate-800/70"
      >
        {title}
        <span className="text-slate-400">{expanded ? '\u25B2' : '\u25BC'}</span>
      </button>
      {expanded && <div>{children}</div>}
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin text-cyan-300"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

export default App
