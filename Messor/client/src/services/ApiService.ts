import type { ScrapingSession } from '../types';

// ── types ────────────────────────────────────────────────────────────────────

export interface PaginationMeta {
  page: number;
  pageSize: number;
  pageCount: number;
  total: number;
}

export interface OutletStat {
  name: string;
  slug: string;
  articles: number;
}

export interface SessionRecord {
  id: string;
  documentId: string;
  start_time: string;
  end_time: string;
  total_articles: number;
  successful_articles: number;
  failed_articles: number;
  duration: number;
  success_rate: number;
  /** Comma-joined display string for the first 3 outlets */
  outlet: string;
  outlets: OutletStat[];
  total_outlets: number;
  views: number;
  last_viewed: string | null;
}

interface SessionsResponse {
  data: SessionRecord[];
  meta: { pagination: PaginationMeta };
}

export interface FetchScrapingResultsOptions {
  limit?: number;
  page?: number;
  filterToday?: boolean;
  filterOutlet?: string;
  startDate?: string;
  endDate?: string;
}

export interface MessorOutlet {
  id: string;
  name: string;
  display_name: string;
  url: string;
  region: string;
  language: string;
  vertical: string;
  active: boolean;
  priority: number;
}

export interface ScraperStatus {
  running: boolean;
  last_run_at: string | null;
  outlets_scraped: number;
  articles_collected: number;
  total_sessions: number;
  status: string;
}

type ScrapingSessionWithMeta = ScrapingSession & {
  start_time: string;
  end_time: string;
  outlets?: OutletStat[];
  total_outlets?: number;
  meta?: { pagination?: PaginationMeta };
};

// ── ApiService ───────────────────────────────────────────────────────────────

export class ApiService {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
    if (this.apiKey && !['default-api-key', 'ghyuhjbjhjhhjhjhj'].includes(this.apiKey)) {
      headers.Authorization = `Bearer ${this.apiKey}`;
    }
    const res = await fetch(url, { headers, mode: 'cors', ...options });
    if (!res.ok) throw new Error(`API ${endpoint} → ${res.status}`);
    return res.json() as Promise<T>;
  }

  // ── sessions ──────────────────────────────────────────────────────────────

  private _transform(record: SessionRecord, pagination?: PaginationMeta): ScrapingSessionWithMeta {
    return {
      id:                    record.id,
      start_time:            record.start_time,
      end_time:              record.end_time,
      total_outlets_scraped: record.total_outlets,
      total_articles_scraped:record.total_articles,
      duration:              record.duration,
      overall_success_rate:  record.success_rate,
      views:                 record.views,
      last_viewed:           record.last_viewed ?? undefined,
      outlets:               record.outlets,
      total_outlets:         record.total_outlets,
      results: record.outlets.map(o => ({
        outlet: { name: o.name, url: `https://${o.slug}.com`, type: 'news' },
        total_articles:     o.articles,
        successful_scrapes: o.articles,
        failed_scrapes:     0,
        duration:           record.duration / Math.max(record.total_outlets, 1),
        errors:             [],
      })),
      meta: pagination ? { pagination } : undefined,
    };
  }

  async fetchScrapingResults(options: FetchScrapingResultsOptions = {}): Promise<ScrapingSessionWithMeta> {
    const params = new URLSearchParams();
    params.set('page',  String(options.page  ?? 1));
    params.set('limit', String(options.limit ?? 10));
    if (options.filterOutlet && options.filterOutlet !== 'All Outlets') {
      params.set('outlet', options.filterOutlet);
    }
    if (options.filterToday) params.set('today', '1');

    const res = await this.request<SessionsResponse>(`/api/scrapesessions?${params}`);
    const pagination = res.meta?.pagination ?? { page: 1, pageSize: 10, pageCount: 1, total: 0 };
    const first = res.data?.[0];

    if (!first) {
      return this._transform({
        id: 'no-data', documentId: 'no-data',
        start_time: new Date().toISOString(), end_time: new Date().toISOString(),
        total_articles: 0, successful_articles: 0, failed_articles: 0,
        duration: 0, success_rate: 0, outlet: 'No data yet',
        outlets: [], total_outlets: 0, views: 0, last_viewed: null,
      }, pagination);
    }
    return this._transform(first, pagination);
  }

  // ── outlets ──────────────────────────────────────────────────────────────

  async getOutlets(): Promise<MessorOutlet[]> {
    return this.request<MessorOutlet[]>('/api/outlets');
  }

  // ── status ───────────────────────────────────────────────────────────────

  async getScrapingStatus(): Promise<ScraperStatus> {
    return this.request<ScraperStatus>('/api/scrape/status');
  }

  // ── view tracking ─────────────────────────────────────────────────────────

  async recordSessionView(sessionId: string): Promise<void> {
    try {
      await this.request(`/api/scrape/session/${sessionId}/view`, { method: 'POST' });
    } catch {
      // non-critical
    }
  }
}
