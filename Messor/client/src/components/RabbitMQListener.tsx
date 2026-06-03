import React, { useEffect, useRef } from 'react';

interface RabbitMQListenerProps {
    onMessage: (message: string) => void;
}

/**
 * RabbitMQListener - Simulates receiving messages from RabbitMQ
 * 
 * In a real implementation, this would connect to a RabbitMQ server
 * and subscribe to relevant queues.
 * 
 * Features:
 * - Minimal message display to avoid console clutter
 * - Only shows messages when actual article processing happens
 * - Occasional important operational messages
 */
const RabbitMQListener: React.FC<RabbitMQListenerProps> = ({ onMessage }) => {
    // Keep track of interval IDs for cleanup
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const isScrapingRef = useRef<boolean>(false);
    
    useEffect(() => {
        // Article-related messages for when scraping is active
        const articleMessages = [
            "Received article data from outlet 'theguardian', ID: GRD-75432",
            "Processing 5 new articles from 'bbc'",
            "Article 'COVID-19 Updates' saved with ID: ART-54321",
            "Extracted metadata for article BBC-87631: categories=[politics, health]",
            "Content extraction completed for article NYT-98745",
            "Processing 3 new articles from 'cnn', priority=high",
            "Sending article WP-65432 to analytics processing",
            "Article batch processing complete: 12 articles from 3 outlets",
        ];
        
        // Important operational messages (very rare)
        const operationalMessages = [
            "Queue 'messor.articles' has 37 pending messages",
            "Queue statistics: messor.articles=8, messor.logs=3, messor.commands=0",
            "WARNING: Queue 'messor.articles' reaching high water mark (85% full)",
            "Heartbeat acknowledged from server",
            "Consumer tag 'articles_consumer' acknowledged by server",
        ];
        
        // Initial connection - only send this once at the beginning
        setTimeout(() => {
            onMessage("Connection established with rabbitmq-server:5672");
            
            // After 5 seconds, add the consumer registration message
            setTimeout(() => {
                onMessage("Consumer for queue 'messor.articles' registered with tag 'articles_consumer'");
            }, 5000);
        }, 2000);
        
        // Function to simulate beginning a scraping session
        const startScraping = () => {
            if (isScrapingRef.current) return;
            
            isScrapingRef.current = true;
            let remainingArticles = Math.floor(Math.random() * 30) + 5; // 5-35 articles to process
            
            onMessage("Queue 'messor.articles' receiving new batch of articles");
            
            // Process 1-3 articles at a time with a delay between each batch
            const processArticleBatch = () => {
                if (remainingArticles <= 0) {
                    // All articles processed
                    onMessage("Message processing completed for batch #" + Math.floor(Math.random() * 10000));
                    isScrapingRef.current = false;
                    return;
                }
                
                // Process 1-3 articles
                const batchSize = Math.min(Math.floor(Math.random() * 3) + 1, remainingArticles);
                remainingArticles -= batchSize;
                
                // Select a random article message
                const articleMessage = articleMessages[Math.floor(Math.random() * articleMessages.length)];
                onMessage(articleMessage);
                
                // Schedule next batch after 10-15 seconds
                setTimeout(processArticleBatch, Math.floor(Math.random() * 5000) + 10000);
            };
            
            // Start processing articles
            processArticleBatch();
        };
        
        // Start a scraping session every 3-5 minutes (180000-300000 ms)
        const scheduleScrapingSession = () => {
            const delay = Math.floor(Math.random() * 120000) + 180000;
            intervalRef.current = setTimeout(() => {
                startScraping();
                scheduleScrapingSession();
            }, delay);
        };
        
        // Schedule an occasional operational message every 2-4 minutes (120000-240000 ms)
        const scheduleOperationalMessage = () => {
            const delay = Math.floor(Math.random() * 120000) + 120000;
            setTimeout(() => {
                // Only show operational messages infrequently
                if (!isScrapingRef.current && Math.random() > 0.7) {
                    const operationalMessage = operationalMessages[Math.floor(Math.random() * operationalMessages.length)];
                    onMessage(operationalMessage);
                }
                scheduleOperationalMessage();
            }, delay);
        };
        
        // Schedule first scraping session after 30-60 seconds
        setTimeout(() => {
            startScraping();
            scheduleScrapingSession();
            scheduleOperationalMessage();
        }, Math.floor(Math.random() * 30000) + 30000);
        
        // Cleanup on unmount
        return () => {
            if (intervalRef.current) {
                clearTimeout(intervalRef.current);
            }
        };
    }, [onMessage]);

    return null;
};

export default RabbitMQListener;
