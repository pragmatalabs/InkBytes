// frontend/src/components/RabbitMQListener.js
import  { useEffect, useState } from 'react';

const RabbitMQListener: React.FC = () => {
    const [messages, setMessages] = useState<string[]>([]);

    useEffect(() => {
        // Connect to WebSocket server
        const ws = new WebSocket('ws://localhost:7701');

        ws.onopen = () => {
            console.log('Connected to WebSocket server');
        };

        ws.onmessage = (event) => {
            const newMessage = event.data;
            setMessages((prevMessages) => [...prevMessages, newMessage]);
        };

        ws.onclose = () => {
            console.log('Disconnected from WebSocket server');
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        // Clean up WebSocket connection on component unmount
        return () => {
            ws.close();
        };
    }, []);


    return (
        <div>
            <h2>RabbitMQ Messages</h2>
            <ul>
                {messages.map((msg, index) => (
                    <li key={index}>{msg}</li>
                ))}
            </ul>
        </div>
    );
};

export default RabbitMQListener;
