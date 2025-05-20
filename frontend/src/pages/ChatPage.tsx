import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Paper, Tabs, Tab, Container, Button } from '@mui/material';
import ChatInterface from '../components/chat/ChatInterface';
import PromptTemplates from '../components/chat/PromptTemplates';
import { useChat, UseChatReturn } from '../hooks/useChat'; // Import the hook
import { useAppDispatch } from '../hooks/redux';
import { clearChat, setInputPrompt, addMessage } from '../store/slices/chatSlice'; // Import addMessage
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import { v4 as uuidv4 } from 'uuid'; // For generating ID for the greeting message
import { ChatMessageUI } from '../types/index.ts'; // For the type of the greeting message

const GREETING_MESSAGE_CONTENT = 'Hello! How can I assist you today?';

const createGreetingMessage = (): ChatMessageUI => ({
  id: uuidv4(),
  role: 'assistant',
  content: GREETING_MESSAGE_CONTENT,
  timestamp: new Date(),
});

const ChatPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const chatHookData: UseChatReturn = useChat(); // Use the hook
  const dispatch = useAppDispatch();

  const handleChangeTab = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleNewChat = () => {
    dispatch(clearChat());
    // Optionally switch to chat tab if not already there
    if (activeTab !== 0) {
      setActiveTab(0);
    }
  };
  
  const applyTemplateAndSwitch = useCallback((prompt: string) => {
    dispatch(setInputPrompt(prompt));
    setActiveTab(0); // Switch to the "Chat" tab
  }, [dispatch]);

  // Effect to add greeting message if chat is empty
  useEffect(() => {
    // Check if messages array is empty and the greeting isn't already the only message
    // This prevents adding multiple greetings if the effect re-runs quickly for some reason
    if (chatHookData.messages.length === 0) {
      dispatch(addMessage(createGreetingMessage()));
    } else if (chatHookData.messages.length === 1 && chatHookData.messages[0].content === GREETING_MESSAGE_CONTENT && chatHookData.messages[0].role === 'assistant') {
      // Greeting is already there, do nothing
    } else if (chatHookData.messages.length > 0 && chatHookData.messages.every(msg => msg.role !== 'assistant' || msg.content !== GREETING_MESSAGE_CONTENT)) {
        // This case is less likely if the first check handles empty, but as a safeguard:
        // If messages exist but none are the greeting, and we decide a greeting is *always* needed if no other assistant message is first,
        // logic could be added here. For now, we only add if completely empty.
    }
  }, [chatHookData.messages, dispatch]); // Depend on messages array and dispatch

  useEffect(() => {
    // This custom event listener is no longer strictly needed if applyTemplateAndSwitch is passed down
    // However, if PromptTemplates dispatches an event for other purposes, it can remain.
    // For now, we'll rely on the direct callback.
    const handleSwitchToChatTab = (event: CustomEvent) => {
      if (event.detail && event.detail.prompt) {
        dispatch(setInputPrompt(event.detail.prompt));
      }
      setActiveTab(0); 
    };
    window.addEventListener('template-applied-switch-tab', handleSwitchToChatTab as EventListener);
    return () => {
      window.removeEventListener('template-applied-switch-tab', handleSwitchToChatTab as EventListener);
    };
  }, [dispatch]);

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
          Chat Assistant
        </Typography>
        <Button
          variant="outlined"
          startIcon={<AddCircleOutlineIcon />}
          onClick={handleNewChat}
        >
          New Chat
        </Button>
      </Box>
      <Paper elevation={3}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={handleChangeTab} aria-label="chat tabs" variant="fullWidth">
            <Tab label="Chat" id="chat-tab-0" aria-controls="chat-tabpanel-0" />
            <Tab label="Prompt Templates" id="chat-tab-1" aria-controls="chat-tabpanel-1" />
          </Tabs>
        </Box>
        <TabPanel value={activeTab} index={0}>
          {/* Pass all props from useChat hook to ChatInterface */}
          <ChatInterface {...chatHookData} />
        </TabPanel>
        <TabPanel value={activeTab} index={1}>
          {/* Pass applyTemplate to PromptTemplates */}
          <PromptTemplates applyTemplate={applyTemplateAndSwitch} />
        </TabPanel>
      </Paper>
    </Container>
  );
};

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`chat-tabpanel-${index}`}
      aria-labelledby={`chat-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default ChatPage; 