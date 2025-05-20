import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Paper, Tabs, Tab, Container, Button } from '@mui/material';
import ChatInterface from '../components/chat/ChatInterface';
import PromptTemplates from '../components/chat/PromptTemplates';
import { useChat, UseChatReturn } from '../hooks/useChat'; // Import the hook
import { useAppDispatch } from '../hooks/redux';
import { clearChat, setInputPrompt } from '../store/slices/chatSlice';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';

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