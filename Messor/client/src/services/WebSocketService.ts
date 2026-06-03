// src/services/WebSocketService.ts
export class WebSocketService {
  private socket: WebSocket | null = null;
  private messageHandlers: Array<(message: string) => void> = [];
  private connectionHandlers: Array<(status: boolean) => void> = [];
  private errorHandlers: Array<(error: Event) => void> = [];

  constructor(private url: string) {}

  connect(retries = 3): Promise<void> {
    return new Promise((resolve, reject) => {
      const attemptConnection = (attemptsLeft: number) => {
        console.log(`Attempting to connect to WebSocket at: ${this.url}`);

        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
          console.log('Connected to WebSocket');
          this.notifyConnectionHandlers(true);
          resolve();
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.notifyErrorHandlers(error);
          
          if (attemptsLeft > 0) {
            console.log(`Retrying connection. ${attemptsLeft} attempts left.`);
            setTimeout(() => attemptConnection(attemptsLeft - 1), 2000);
          } else {
            reject(new Error('Failed to connect after multiple attempts'));
          }
        };

        this.socket.onclose = (event) => {
          console.log(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
          this.notifyConnectionHandlers(false);
          
          if (!event.wasClean) {
            console.error('WebSocket closed unexpectedly');
          }
        };

        this.socket.onmessage = (event) => {
          console.log('Received message:', event.data);
          this.notifyMessageHandlers(event.data);
        };
      };

      attemptConnection(retries);
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  send(message: string): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    this.socket.send(message);
  }

  addMessageHandler(handler: (message: string) => void): void {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler: (message: string) => void): void {
    this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
  }

  addConnectionHandler(handler: (status: boolean) => void): void {
    this.connectionHandlers.push(handler);
  }

  removeConnectionHandler(handler: (status: boolean) => void): void {
    this.connectionHandlers = this.connectionHandlers.filter(h => h !== handler);
  }

  addErrorHandler(handler: (error: Event) => void): void {
    this.errorHandlers.push(handler);
  }

  removeErrorHandler(handler: (error: Event) => void): void {
    this.errorHandlers = this.errorHandlers.filter(h => h !== handler);
  }

  private notifyMessageHandlers(message: string): void {
    this.messageHandlers.forEach(handler => handler(message));
  }

  private notifyConnectionHandlers(status: boolean): void {
    this.connectionHandlers.forEach(handler => handler(status));
  }

  private notifyErrorHandlers(error: Event): void {
    this.errorHandlers.forEach(handler => handler(error));
  }

  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }
}