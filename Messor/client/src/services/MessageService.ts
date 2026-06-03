// src/services/MessageService.ts
import { WebSocketService } from './WebSocketService';

export class MessageService {
  private wsService: WebSocketService | null = null;
  private simulationInterval: NodeJS.Timeout | null = null;
  private readonly useSimulation: boolean;

  constructor(websocketUrl: string = 'ws://localhost:7701', useSimulation: boolean = false) {
    this.useSimulation = useSimulation;
    
    if (!useSimulation) {
      this.wsService = new WebSocketService(websocketUrl);
    }
  }

  connect(): Promise<void> {
    if (this.useSimulation) {
      // No actual connection for simulation
      return Promise.resolve();
    }
    
    return this.wsService?.connect() || Promise.reject(new Error('WebSocket service not initialized'));
  }

  startListening(onMessage: (message: string) => void): void {
    if (this.useSimulation) {
      // Start simulation if enabled
      this.startSimulation(onMessage);
    } else if (this.wsService) {
      // Use actual WebSocket
      this.wsService.addMessageHandler(onMessage);
    }
  }

  stopListening(onMessage?: (message: string) => void): void {
    if (this.useSimulation) {
      this.stopSimulation();
    } else if (this.wsService && onMessage) {
      this.wsService.removeMessageHandler(onMessage);
    }
  }

  private startSimulation(onMessage: (message: string) => void): void {
    // Clear any existing simulation
    this.stopSimulation();
    
    // Start new simulation interval
    this.simulationInterval = setInterval(() => {
      const message = `Simulated message at ${new Date().toLocaleTimeString()}`;
      onMessage(message);
    }, 5000);
  }

  private stopSimulation(): void {
    if (this.simulationInterval) {
      clearInterval(this.simulationInterval);
      this.simulationInterval = null;
    }
  }

  disconnect(): void {
    this.stopSimulation();
    if (this.wsService) {
      this.wsService.disconnect();
      this.wsService = null;
    }
  }

  isConnected(): boolean {
    if (this.useSimulation) {
      return this.simulationInterval !== null;
    }
    return this.wsService?.isConnected() || false;
  }
}