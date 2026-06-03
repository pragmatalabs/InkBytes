import React, { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { Box, Typography, Paper, TextField, InputAdornment } from '@mui/material';

interface LogMessage {
  timestamp: string;
  message: string;
  level: 'info' | 'error' | 'warning' | 'success';
}

interface ConsoleLogProps {
  logs: LogMessage[];
  title?: string;
  maxHeight?: number | string;
  autoScroll?: boolean;
  onCommand?: (command: string) => void;
}

/**
 * ConsoleLog component - An interactive CLI console-like component for displaying logs
 * 
 * Features:
 * - Terminal-like appearance with monospace font
 * - Color-coded log levels
 * - Auto-scrolling to latest logs
 * - Command input with history
 * - Timestamp display
 */
const ConsoleLog: React.FC<ConsoleLogProps> = ({
  logs,
  title = 'Console',
  maxHeight = 300,
  autoScroll = true,
  onCommand
}) => {
  const consoleRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [commandInput, setCommandInput] = useState<string>('');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [isFocused, setIsFocused] = useState<boolean>(false);

  // Auto-scroll to bottom when logs update
  useEffect(() => {
    if (autoScroll && consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Focus input when clicking on console
  const handleConsoleClick = () => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Handle command submission
  const handleCommandSubmit = () => {
    if (commandInput.trim()) {
      // Add to history
      setCommandHistory(prev => [...prev, commandInput]);
      setHistoryIndex(-1);
      
      // Call the onCommand callback if provided
      if (onCommand) {
        onCommand(commandInput);
      }
      
      // Clear input
      setCommandInput('');
    }
  };

  // Available commands for tab completion
  const availableCommands = [
    'help',
    'scrape',
    'status',
    'clear',
    'connect',
    'about',
    'rabbit',
    'rabbit status',
    'rabbit info'
  ];
  
  // Tab completion function
  const getCompletions = (input: string): string[] => {
    if (!input) return availableCommands;
    
    const normalizedInput = input.toLowerCase();
    return availableCommands.filter(cmd => 
      cmd.toLowerCase().startsWith(normalizedInput)
    );
  };
  
  // Handle key navigation for command history and tab completion
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCommandSubmit();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIndex);
        setCommandInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommandInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setCommandInput('');
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      
      // Get possible completions
      const completions = getCompletions(commandInput);
      
      if (completions.length === 1) {
        // If only one completion, use it
        setCommandInput(completions[0]);
      } else if (completions.length > 1) {
        // If multiple completions, show them as suggestions
        const commonPrefix = findCommonPrefix(completions);
        if (commonPrefix.length > commandInput.length) {
          // If there's a common prefix longer than current input, use it
          setCommandInput(commonPrefix);
        } else {
          // Otherwise, display available completions
          addCompletionsToLogs(completions);
        }
      }
    }
  };
  
  // Find the common prefix among all completions
  const findCommonPrefix = (strings: string[]): string => {
    if (strings.length === 0) return '';
    if (strings.length === 1) return strings[0];
    
    let prefix = strings[0];
    for (let i = 1; i < strings.length; i++) {
      let j = 0;
      while (j < prefix.length && j < strings[i].length && prefix[j] === strings[i][j]) {
        j++;
      }
      prefix = prefix.substring(0, j);
      if (prefix === '') break;
    }
    
    return prefix;
  };
  
  // Add completions as a temporary log message
  const addCompletionsToLogs = (completions: string[]) => {
    if (onCommand) {
      const formattedCompletions = completions.join('  ');
      onCommand(`__COMPLETIONS__:${formattedCompletions}`);
    }
  };

  // Get proper color for log level
  const getLevelColor = (level: LogMessage['level']): string => {
    switch (level) {
      case 'error': return '#ff5252'; // Red
      case 'warning': return '#ffb74d'; // Orange
      case 'success': return '#66bb6a'; // Green
      case 'info':
      default: return '#4fc3f7'; // Blue
    }
  };

  // Get proper prefix for log level
  const getLevelPrefix = (level: LogMessage['level']): string => {
    switch (level) {
      case 'error': return 'ERR!';
      case 'warning': return 'WARN';
      case 'success': return 'DONE';
      case 'info':
      default: return 'INFO';
    }
  };

  return (
    <>
      {title && (
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6">{title}</Typography>
          <Box sx={{ 
            ml: 1, 
            px: 1, 
            py: 0.5, 
            bgcolor: 'grey.200', 
            borderRadius: 1, 
            fontSize: '0.75rem',
            fontFamily: 'monospace'
          }}>
            {logs.length} entries
          </Box>
        </Box>
      )}
      
      <Paper
        ref={consoleRef}
        variant="outlined"
        onClick={handleConsoleClick}
        sx={{
          bgcolor: '#1e1e1e', // Dark background like a terminal
          color: '#f8f8f8',    // Light text color
          p: 2,
          maxHeight: maxHeight,
          height: '100%',
          overflow: 'auto',
          fontFamily: 'monospace',
          fontSize: '0.9rem',
          border: '1px solid #333',
          borderRadius: 1,
          cursor: 'text',
          position: 'relative',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            bgcolor: 'rgba(0,0,0,0.1)',
          },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: 'rgba(255,255,255,0.2)',
            borderRadius: '4px',
          },
        }}
      >
        {/* Console Header */}
        <Box sx={{ 
          pb: 1, 
          mb: 1, 
          borderBottom: '1px solid #333',
          display: 'flex',
          justifyContent: 'space-between'
        }}>
          <Typography component="span" sx={{ color: '#aaa' }}>
            Messor CLI v1.0.0
          </Typography>
          <Typography component="span" sx={{ color: '#aaa' }}>
            Type 'help' for commands
          </Typography>
        </Box>
        
        {/* Display logs */}
        {logs.length > 0 ? (
          logs.map((log, index) => (
            <Box 
              key={index}
              sx={{ 
                my: 0.5,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: 'monospace'
              }}
            >
              {/* Timestamp */}
              <Typography component="span" sx={{ color: '#888', mr: 1 }}>
                [{new Date(log.timestamp).toLocaleTimeString()}]
              </Typography>
              
              {/* Log level */}
              <Typography 
                component="span" 
                sx={{ 
                  color: getLevelColor(log.level),
                  fontWeight: 'bold',
                  mr: 1
                }}
              >
                [{getLevelPrefix(log.level)}]
              </Typography>
              
              {/* Message */}
              <Typography component="span">
                {log.message}
              </Typography>
            </Box>
          ))
        ) : (
          <Box sx={{ color: '#888', fontStyle: 'italic' }}>
            No logs yet. Operations will appear here.
          </Box>
        )}
        
        {/* Command prompt with input field */}
        <Box sx={{ 
          display: 'flex',
          alignItems: 'center',
          mt: 1,
          pt: 1,
          borderTop: '1px solid #333',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <TextField
              ref={inputRef}
              value={commandInput}
              onChange={(e) => setCommandInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              variant="standard"
              fullWidth
              autoComplete="off"
              spellCheck="false"
              placeholder={isFocused ? '' : 'Type a command...'}
              InputProps={{
                disableUnderline: true,
                startAdornment: (
                  <InputAdornment position="start">
                    <Typography component="span" sx={{ color: '#4caf50', fontFamily: 'monospace' }}>
                      messor@inkbytes:~$
                    </Typography>
                  </InputAdornment>
                ),
                sx: {
                  px: 0,
                  py: 0,
                  color: '#f8f8f8',
                  fontFamily: 'monospace',
                  fontSize: '0.9rem',
                  '& input': {
                    px: 1,
                    py: 0,
                  },
                  '&::placeholder': {
                    color: 'rgba(255,255,255,0.3)',
                    opacity: 1,
                  },
                }
              }}
            />
            {!isFocused && commandInput === '' && (
              <Box 
                component="span" 
                sx={{ 
                  position: 'absolute',
                  right: 16,
                  display: 'inline-block',
                  width: '8px',
                  height: '18px',
                  bgcolor: '#f8f8f8',
                  animation: 'blink 1s step-end infinite',
                  '@keyframes blink': {
                    '0%': { opacity: 1 },
                    '50%': { opacity: 0 },
                    '100%': { opacity: 1 },
                  }
                }} 
              />
            )}
          </Box>
        </Box>
      </Paper>
    </>
  );
};

export default ConsoleLog;