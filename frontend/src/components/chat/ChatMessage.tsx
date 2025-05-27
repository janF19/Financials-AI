import React from 'react';
import { Box, Paper, Typography, Avatar, Chip, Tooltip } from '@mui/material';
import { Person as UserIcon, Assistant as AssistantIcon, AttachFile as AttachFileIcon } from '@mui/icons-material';

import { ChatMessageUI } from '../../types/index.ts';

interface ChatMessageProps {
  message: ChatMessageUI;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  // Ensure timestamp is a Date object before formatting
  let timestampDate: Date;
  if (message.timestamp instanceof Date) {
    timestampDate = message.timestamp;
  } else if (typeof message.timestamp === 'string') {
    timestampDate = new Date(message.timestamp); // Convert string to Date
  } else {
    // Fallback for unexpected timestamp type, though ideally this shouldn't happen
    timestampDate = new Date();
    console.warn("Unexpected timestamp type:", message.timestamp);
  }

  // Defensive check for invalid date string conversion
  const timeString = !isNaN(timestampDate.getTime())
    ? timestampDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'Invalid time';

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', flexDirection: isUser ? 'row-reverse' : 'row', maxWidth: '80%' }}>
        <Avatar sx={{ bgcolor: isUser ? 'secondary.main' : 'primary.main', ml: isUser ? 1 : 0, mr: isUser ? 0 : 1 }}>
          {isUser ? <UserIcon /> : <AssistantIcon />}
        </Avatar>
        <Paper
          elevation={1}
          sx={{
            p: 1.5,
            bgcolor: isUser ? 'primary.light' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
            borderRadius: isUser ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
          }}
        >
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {message.content}
          </Typography>
          {isUser && message.fileDisplayName && (
            <Chip
              icon={<AttachFileIcon />}
              label={message.fileDisplayName}
              size="small"
              sx={{ mt: 1, backgroundColor: 'rgba(255,255,255,0.2)', color: 'white' }}
            />
          )}
          <Tooltip title={timestampDate.toLocaleString()} placement={isUser ? "top-start" : "top-end"}>
            <Typography
              variant="caption"
              display="block"
              sx={{
                mt: 0.5,
                textAlign: isUser ? 'right' : 'left',
                color: isUser ? 'rgba(255,255,255,0.7)' : 'text.secondary',
              }}
            >
              {timeString}
            </Typography>
          </Tooltip>
        </Paper>
      </Box>
    </Box>
  );
};

export default ChatMessage; 