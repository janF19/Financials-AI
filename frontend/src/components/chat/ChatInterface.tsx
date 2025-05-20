import React, { useRef, useEffect, useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  IconButton,
  CircularProgress,
  //Typography,
  Chip
  //Alert
} from '@mui/material';
import { Send as SendIcon, AttachFile as AttachFileIcon, DeleteSweep as DeleteSweepIcon } from '@mui/icons-material';
import ChatMessage from './ChatMessage';
import FileUploadDialog from './FileUploadDialog'; // Import the dialog
import { UseChatReturn } from '../../hooks/useChat'; // Import the hook's return type

// Styles for typing indicator (inspired by your example)
const typingIndicatorStyles = {
  display: 'flex',
  alignItems: 'center',
  padding: '8px 12px',
  backgroundColor: 'action.hover', // MUI theme color
  borderRadius: '12px',
  width: 'fit-content',
  ml: '58px', // To align with assistant messages
  mb: 1,
  '& span': {
    width: '8px',
    height: '8px',
    margin: '0 2px',
    backgroundColor: 'primary.main', // MUI theme color
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'typing 1.4s infinite ease-in-out both',
  },
  '& span:nth-of-type(1)': { animationDelay: '0s' },
  '& span:nth-of-type(2)': { animationDelay: '0.2s' },
  '& span:nth-of-type(3)': { animationDelay: '0.4s' },
  '@keyframes typing': {
    '0%': { transform: 'scale(0.9)', opacity: 0.7 },
    '50%': { transform: 'scale(1.1)', opacity: 1 },
    '100%': { transform: 'scale(0.9)', opacity: 0.7 },
  },
};


const ChatInterface: React.FC<UseChatReturn> = ({
  messages,
  input,
  setInput,
  isLoading,
  // error, // error is handled by toast in useChat, but can be displayed here too
  sendMessage,
  clearMessages,
  uploadedFile,
  setUploadedFile,
  handleFileUpload,
  isUploading,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages, isLoading]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    await sendMessage();
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 280px)', maxHeight: '700px' /* Adjust as needed */ }}>
      <Paper
        elevation={0}
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          p: 2,
          mb: 2,
          backgroundColor: 'grey.100', // Light background for message area
          borderRadius: 1,
        }}
      >
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isLoading && (
          <Box sx={typingIndicatorStyles}>
            <span /><span /><span />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {uploadedFile && (
        <Chip
          icon={<AttachFileIcon />}
          label={`Attached: ${uploadedFile.display_name}`}
          onDelete={() => setUploadedFile(null)}
          color="info"
          sx={{ mb: 1, maxWidth: 'fit-content', alignSelf: 'flex-start' }}
        />
      )}

      <Box component="form" onSubmit={handleSendMessage} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <IconButton onClick={() => setIsFileUploadOpen(true)} color="primary" aria-label="attach file" disabled={isUploading || !!uploadedFile}>
          <AttachFileIcon />
        </IconButton>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Type your message here..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          multiline
          maxRows={4}
          disabled={isLoading || isUploading}
          size="small"
        />
        <Button
          type="submit"
          variant="contained"
          color="primary"
          disabled={isLoading || isUploading || (!input.trim() && !uploadedFile)}
          endIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
        >
          Send
        </Button>
         <IconButton onClick={clearMessages} color="default" aria-label="clear chat" title="Clear Chat History" disabled={isLoading || isUploading}>
          <DeleteSweepIcon />
        </IconButton>
      </Box>

      <FileUploadDialog
        open={isFileUploadOpen}
        onClose={() => setIsFileUploadOpen(false)}
        onFileUpload={async (file) => {
          await handleFileUpload(file);
          // Dialog will show success, user can close it or it auto-closes on success in some designs
          // For now, let's keep it simple: if upload is successful, the chip will appear.
          // We might want to close the dialog automatically on successful upload.
          if (!isUploading && uploadedFile) { // Check if upload was successful (uploadedFile is set)
             // setIsFileUploadOpen(false); // Optionally close dialog on success
          }
        }}
        isUploading={isUploading}
        uploadedFileDisplayName={uploadedFile?.display_name}
      />
    </Box>
  );
};

export default ChatInterface; 