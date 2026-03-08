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
        if (s.has_draft) {
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
    <div className="min-h-screen bg-[#0D1117] text-[#E6EDF3]">
      {/* Header */}
      <header className="border-b border-[#30363D] px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              <span className="text-[#20D3BE]">cyber</span>-content-bot
            </h1>
            <p className="mt-1 text-sm text-[#8B949E]">
              Last run: {formatTime(status?.last_run ?? null)}
            </p>
          </div>
          <button
            onClick={handleRun}
            disabled={loading}
            className="rounded-lg bg-[#20D3BE] px-5 py-2.5 text-sm font-semibold text-[#0D1117] transition-opacity hover:opacity-90 disabled:opacity-50"
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

      <main className="mx-auto max-w-4xl space-y-6 p-6">
        {/* Status Bar */}
        <div className="flex flex-wrap gap-4 rounded-lg border border-[#30363D] bg-[#161B22] p-4 text-sm">
          <StatusPill
            label="Scheduler"
            value={status?.scheduler_running ? 'Active' : 'Inactive'}
            active={status?.scheduler_running ?? false}
          />
          <StatusPill
            label="Findings"
            value={String(status?.num_findings ?? 0)}
          />
          <StatusPill
            label="Next Run"
            value={formatTime(status?.next_run ?? null)}
          />
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center gap-3 rounded-lg border border-[#30363D] bg-[#161B22] p-12">
            <Spinner />
            <span className="text-[#8B949E]">
              Fetching sources and generating draft... this may take 10-15 seconds
            </span>
          </div>
        )}

        {/* Draft Card */}
        {draftData?.draft && !loading && (
          <div className="rounded-lg border border-[#30363D] bg-[#161B22]">
            <div className="flex items-center justify-between border-b border-[#30363D] px-5 py-3">
              <h2 className="font-semibold">LinkedIn Draft</h2>
              <button
                onClick={handleCopy}
                className="rounded-md border border-[#30363D] px-3 py-1.5 text-xs font-medium text-[#8B949E] transition-colors hover:border-[#20D3BE] hover:text-[#20D3BE]"
              >
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
            </div>
            <div className="p-5">
              <p className="whitespace-pre-wrap leading-relaxed text-[#E6EDF3]">
                {draftData.draft}
              </p>
            </div>
            <div className="flex items-center gap-3 border-t border-[#30363D] px-5 py-3">
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="rounded-md border border-[#30363D] bg-[#0D1117] px-3 py-1.5 text-sm text-[#E6EDF3] outline-none focus:border-[#20D3BE]"
              >
                <option value="professional">Professional</option>
                <option value="conversational">Conversational</option>
                <option value="technical">Technical</option>
              </select>
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="rounded-md border border-[#20D3BE] px-4 py-1.5 text-sm font-medium text-[#20D3BE] transition-opacity hover:opacity-80 disabled:opacity-50"
              >
                {regenerating ? 'Regenerating...' : 'Regenerate'}
              </button>
            </div>
          </div>
        )}

        {/* No Draft State */}
        {!draftData?.draft && !loading && (
          <div className="rounded-lg border border-[#30363D] bg-[#161B22] p-12 text-center">
            <p className="text-[#8B949E]">
              No draft yet. Click <span className="text-[#20D3BE]">Run Now</span> to
              fetch sources and generate a LinkedIn post.
            </p>
          </div>
        )}

        {/* Sources Panel */}
        {draftData && hasFindings(draftData) && !loading && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[#8B949E]">
              Sources
            </h2>

            {/* NVD CVEs */}
            <SourceSection
              title={`NVD CVEs (${draftData.findings.nvd.length})`}
              expanded={expandedSources['nvd'] ?? false}
              onToggle={() => toggleSource('nvd')}
            >
              {draftData.findings.nvd.map((cve) => (
                <div
                  key={cve.cve_id}
                  className="border-b border-[#30363D] px-5 py-3 last:border-0"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-[#20D3BE]">
                      {cve.cve_id}
                    </span>
                    <SeverityBadge score={cve.cvss_score} severity={cve.severity} />
                  </div>
                  <p className="mt-1 text-sm text-[#8B949E] line-clamp-2">
                    {cve.description}
                  </p>
                  {cve.affected_products.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {cve.affected_products.map((p) => (
                        <span
                          key={p}
                          className="rounded bg-[#0D1117] px-2 py-0.5 text-xs text-[#8B949E]"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </SourceSection>

            {/* CISA Advisories */}
            <SourceSection
              title={`CISA KEV (${draftData.findings.cisa.length})`}
              expanded={expandedSources['cisa'] ?? false}
              onToggle={() => toggleSource('cisa')}
            >
              {draftData.findings.cisa.map((adv) => (
                <div
                  key={adv.cve_id}
                  className="border-b border-[#30363D] px-5 py-3 last:border-0"
                >
                  <div className="font-mono text-sm text-[#20D3BE]">
                    {adv.cve_id}
                  </div>
                  <p className="mt-1 text-sm font-medium">{adv.vulnerability_name}</p>
                  <p className="text-sm text-[#8B949E]">
                    {adv.vendor_project} &mdash; {adv.product}
                  </p>
                  <p className="mt-1 text-xs text-[#8B949E]">
                    Action: {adv.required_action}
                  </p>
                </div>
              ))}
            </SourceSection>

            {/* arXiv Papers */}
            <SourceSection
              title={`arXiv Papers (${draftData.findings.arxiv.length})`}
              expanded={expandedSources['arxiv'] ?? false}
              onToggle={() => toggleSource('arxiv')}
            >
              {draftData.findings.arxiv.map((paper) => (
                <div
                  key={paper.link}
                  className="border-b border-[#30363D] px-5 py-3 last:border-0"
                >
                  <a
                    href={paper.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-[#20D3BE] hover:underline"
                  >
                    {paper.title}
                  </a>
                  <p className="mt-1 text-xs text-[#8B949E]">
                    {paper.authors.join(', ')}
                  </p>
                  <p className="mt-1 text-sm text-[#8B949E] line-clamp-3">
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
    <div className="flex items-center gap-2">
      {active !== undefined && (
        <span
          className={`h-2 w-2 rounded-full ${active ? 'bg-green-400' : 'bg-[#8B949E]'}`}
        />
      )}
      <span className="text-[#8B949E]">{label}:</span>
      <span>{value}</span>
    </div>
  )
}

function SeverityBadge({ score, severity }: { score: number; severity: string }) {
  const color =
    severity === 'CRITICAL'
      ? 'bg-red-900/50 text-red-400'
      : 'bg-orange-900/50 text-orange-400'
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${color}`}>
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
    <div className="rounded-lg border border-[#30363D] bg-[#161B22]">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-3 text-left text-sm font-medium hover:bg-[#1c2129]"
      >
        {title}
        <span className="text-[#8B949E]">{expanded ? '\u25B2' : '\u25BC'}</span>
      </button>
      {expanded && <div>{children}</div>}
    </div>
  )
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin text-[#20D3BE]"
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
