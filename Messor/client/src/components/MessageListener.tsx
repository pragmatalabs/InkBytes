// src/components/MessageListener.tsx
import React, { useEffect, useState } from 'react';
import { Box, Typography, List, ListItem, ListItemText, Card, CardContent } from '@mui/material';
import { useServices } from '../context/ServiceContext';

interface MessageListenerProps {
  onMessage?: (message: string) => void;
  displayMessages?: boolean;
}

const MessageListener: React.FC<MessageListenerProps> = ({ 
  onMessage,
  displayMessages = false
}) => {
  const { messageService } = useServices();
  const [messages, setMessages] = useState<string[]>([]);

  useEffect(() => {
    // Message handler function
    const handleMessage = (message: string) => {
      if (onMessage) {
        onMessage(message);
      }
      
      if (displayMessages) {
        setMessages(prev => [...prev, message]);
      }
    };

    // Start listening for messages
    messageService.startListening(handleMessage);

    // Cleanup on unmount
    return () => {
      messageService.stopListening(handleMessage);
    };
  }, [messageService, onMessage, displayMessages]);

  // If we're not displaying messages, don't render anything
  if (!displayMessages) {
    return null;
  }

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        Message Queue
      </Typography>
      <Card variant="outlined">
        <CardContent>
          {messages.length > 0 ? (
            <List dense>
              {messages.map((msg, index) => (
                <ListItem key={index}>
                  <ListItemText primary={msg} />
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="body2" color="text.secondary" align="center">
              No messages received yet.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default MessageListener;