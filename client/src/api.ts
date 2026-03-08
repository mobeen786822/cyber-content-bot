export interface Findings {
  nvd: NvdCve[];
  cisa: CisaAdvisory[];
  arxiv: ArxivPaper[];
}

export interface NvdCve {
  cve_id: string;
  description: string;
  cvss_score: number;
  severity: string;
  affected_products: string[];
}

export interface CisaAdvisory {
  cve_id: string;
  vulnerability_name: string;
  vendor_project: string;
  product: string;
  required_action: string;
  due_date: string;
}

export interface ArxivPaper {
  title: string;
  summary: string;
  authors: string[];
  link: string;
}

export interface StatusResponse {
  last_run: string | null;
  num_findings: number;
  has_draft: boolean;
  scheduler_running: boolean;
  next_run: string | null;
}

export interface DraftResponse {
  draft: string | null;
  findings: Findings;
}

const BASE = '/api';

export async function getStatus(): Promise<StatusResponse> {
  const res = await fetch(`${BASE}/status`);
  return res.json();
}

export async function triggerRun(): Promise<void> {
  await fetch(`${BASE}/run`, { method: 'POST' });
}

export async function getDraft(): Promise<DraftResponse> {
  const res = await fetch(`${BASE}/draft`);
  return res.json();
}

export async function regenerateDraft(tone: string): Promise<{ draft: string }> {
  const res = await fetch(`${BASE}/draft/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tone }),
  });
  return res.json();
}
