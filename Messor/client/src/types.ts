// src/types.ts

export interface OutletSource {
    name: string;
    url: string;
    type: string; // This could be an enum if we know all possible types
}

export interface Article {
    title: string;
    content: string;
    published_date: string;
    author?: string;
    url: string;
}

export interface ScrapeResult {
    outlet: OutletSource;
    articles: Article[];
    total_articles: number;
    successful_scrapes: number;
    failed_scrapes: number;
    start_time: string;
    end_time: string;
    duration: number; // in seconds
    errors: string[];
}

export interface ScrapingSession {
    id: string;
    results: ScrapeResult[];
    total_outlets_scraped: number;
    total_articles_scraped: number;
    start_time: string;
    end_time: string;
    duration: number; // in seconds
    overall_success_rate: number;
}

export enum SessionSavingMode {
    SAVE_TO_FILE = 'SAVE_TO_FILE',
    SEND_TO_API = 'SEND_TO_API'
}
// src/types.ts

export interface LogMessage {
  timestamp: string;
  message: string;
  level: 'info' | 'error' | 'warning' | 'success';
}

export interface Outlet {
  name: string;
  url: string;
  type: string;
}

export interface ScrapeResult {
  outlet: Outlet;
  total_articles: number;
  successful_scrapes: number;
  failed_scrapes: number;
  duration: number;
  errors: string[];
}

export interface ScrapingSession {
  id: string;
  total_outlets_scraped: number;
  total_articles_scraped: number;
  overall_success_rate: number;
  duration: number;
  results: ScrapeResult[];
  views?: number; // Number of times this session has been viewed
  last_viewed?: string; // ISO date string of last view time
}