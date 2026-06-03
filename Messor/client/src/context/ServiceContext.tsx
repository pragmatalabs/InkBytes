// src/context/ServiceContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ScraperService } from '../services/ScraperService';
import { MessageService } from '../services/MessageService';
import { ApiService } from '../services/ApiService';

interface ServiceContextType {
  scraperService: ScraperService;
  messageService: MessageService;
  apiService: ApiService;
  isScraperConnected: boolean;
  isMessageServiceConnected: boolean;
}

const ServiceContext = createContext<ServiceContextType | null>(null);

interface ServiceProviderProps {
  children: ReactNode;
  scraperBaseUrl?: string;
  platformApiBaseUrl?: string;
  apiKey?: string;
  messageServiceUrl?: string;
  useSimulatedMessages?: boolean;
}

export const ServiceProvider: React.FC<ServiceProviderProps> = ({
  children,
  scraperBaseUrl = import.meta.env.VITE_API_HOST || 'http://localhost:8050',
  platformApiBaseUrl = import.meta.env.VITE_PLATFORM_API_HOST || 'http://localhost:8080',
  apiKey = import.meta.env.VITE_API_KEY || 'default-api-key',
  messageServiceUrl = 'ws://localhost:7701',
  useSimulatedMessages = true
}) => {
  const [isScraperConnected, setScraperConnected] = useState(false);
  const [isMessageServiceConnected, setMessageServiceConnected] = useState(false);

  // Initialize services
  const scraperService = React.useMemo(() => 
    new ScraperService({ baseUrl: scraperBaseUrl, apiKey }),
  [scraperBaseUrl, apiKey]);
  
  const messageService = React.useMemo(() => 
    new MessageService(messageServiceUrl, useSimulatedMessages),
  [messageServiceUrl, useSimulatedMessages]);
  
  // ApiService reads from the Messor scraper API (same host as WebSocket)
  // platformApiBaseUrl (port 8080 / Laravel) is not used in v0.
  const apiService = React.useMemo(() =>
    new ApiService(scraperBaseUrl, apiKey),
  [scraperBaseUrl, apiKey]);

  // Handle connection state
  useEffect(() => {
    // Handle scraper service connection
    const handleScraperConnection = (status: boolean) => {
      setScraperConnected(status);
    };
    
    scraperService.addConnectionHandler(handleScraperConnection);
    
    // Connect to services
    const connectServices = async () => {
      try {
        await scraperService.connect();
        await messageService.connect();
        setMessageServiceConnected(messageService.isConnected());
      } catch (error) {
        console.error('Failed to connect to services:', error);
      }
    };
    
    connectServices();
    
    // Cleanup on unmount
    return () => {
      scraperService.removeConnectionHandler(handleScraperConnection);
      scraperService.disconnect();
      messageService.disconnect();
    };
  }, [scraperService, messageService]);

  const value = {
    scraperService,
    messageService,
    apiService,
    isScraperConnected,
    isMessageServiceConnected
  };

  return (
    <ServiceContext.Provider value={value}>
      {children}
    </ServiceContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useServices = (): ServiceContextType => {
  const context = useContext(ServiceContext);
  if (!context) {
    throw new Error('useServices must be used within a ServiceProvider');
  }
  return context;
};
