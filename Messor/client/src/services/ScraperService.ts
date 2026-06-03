// src/services/ScraperService.ts
import { WebSocketService } from './WebSocketService';

export interface ScraperOptions {
  apiKey: string;
  baseUrl: string;
}

export class ScraperService {
  private wsService: WebSocketService | null = null;
  private apiKey: string;
  private baseUrl: string;

  constructor(options: ScraperOptions) {
    this.baseUrl = options.baseUrl;
    this.apiKey = options.apiKey;
  }

  connect(retries = 3): Promise<void> {
    const wsUrl = `${this.baseUrl.replace(/^http/, 'ws')}/api/scrape/ws?api_key=${this.apiKey}`;
    this.wsService = new WebSocketService(wsUrl);
    return this.wsService.connect(retries);
  }

  startScrape(
    onLogUpdate: (log: string) => void, 
    onComplete: () => void, 
    onError: (error: unknown) => void
  ): void {
    if (!this.wsService || !this.wsService.isConnected()) {
      throw new Error('Not connected to scraper service');
    }

    // Add specific message handler for the scraping operation
    const messageHandler = (message: string) => {
      if (message === 'Scraping task finished.') {
        onComplete();
        // Remove this handler once the task is complete
        this.wsService?.removeMessageHandler(messageHandler);
      } else {
        onLogUpdate(message);
      }
    };

    // Add error handler
    const errorHandler = (error: Event) => {
      onError(error);
      // Remove handlers once an error occurs
      this.wsService?.removeMessageHandler(messageHandler);
      this.wsService?.removeErrorHandler(errorHandler);
    };

    this.wsService.addMessageHandler(messageHandler);
    this.wsService.addErrorHandler(errorHandler);
    
    // Send command to start scraping
    this.wsService.send('start_scrape');
  }

  addConnectionHandler(handler: (status: boolean) => void): void {
    this.wsService?.addConnectionHandler(handler);
  }

  removeConnectionHandler(handler: (status: boolean) => void): void {
    this.wsService?.removeConnectionHandler(handler);
  }

  isConnected(): boolean {
    return this.wsService?.isConnected() || false;
  }

  disconnect(): void {
    this.wsService?.disconnect();
    this.wsService = null;
  }
}
