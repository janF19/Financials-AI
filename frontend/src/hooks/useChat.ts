import { useState, useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import { v4 as uuidv4 } from 'uuid';
import {
  addMessage,
  sendChatMessage,
  uploadFileForChat,
  setCurrentFile,
  setInputPrompt,
  clearInputPrompt,
} from '../store/slices/chatSlice';
import { ChatMessageUI, ChatState } from '../types/index.ts';

export interface UseChatReturn extends ChatState {
  userInput: string;
  setUserInput: (input: string) => void;
  handleSendMessage: (messageText?: string) => Promise<void>;
  handleFileUpload: (file: File) => Promise<void>;
  clearUploadedFile: () => void;
  applyTemplate: (template: string) => void; // Kept for internal use if needed, or direct dispatch
}

export const useChat = (): UseChatReturn => {
  const dispatch = useAppDispatch();
  const chatState = useAppSelector((state) => state.chat);
  const [userInput, setUserInput] = useState('');

  // Effect to update local userInput when inputPrompt changes in Redux state
  useEffect(() => {
    if (chatState.inputPrompt) {
      setUserInput(chatState.inputPrompt);
      dispatch(clearInputPrompt()); // Clear it from Redux once consumed
    }
  }, [chatState.inputPrompt, dispatch]);

  const handleSendMessage = useCallback(async (messageText?: string) => {
    const messageToSend = (messageText || userInput).trim();
    if (!messageToSend && !chatState.currentFileUri) {
      // Allow sending if only a file is present without text
      if(chatState.currentFileUri && !chatState.isFileContextApplied){
         // If there's a file but no text, we might want to send a default message or just the file.
         // For now, let's assume a message is required or the file is sent with an empty text.
      } else {
        return;
      }
    }

    const userMessage: ChatMessageUI = {
      id: uuidv4(),
      role: 'user',
      content: messageToSend,
      timestamp: new Date(),
      fileDisplayName: (chatState.currentFileUri && !chatState.isFileContextApplied) ? (chatState.currentFileDisplayName ?? undefined) : undefined,
    };
    dispatch(addMessage(userMessage));

    // Pass the file URI that is relevant for THIS message.
    // If isFileContextApplied is true, it means the current file was for a *previous* message.
    const fileUriForThisMessage = chatState.currentFileUri && !chatState.isFileContextApplied
        ? chatState.currentFileUri
        : null;

    await dispatch(sendChatMessage({ message: messageToSend, fileUri: fileUriForThisMessage }));
    
    setUserInput(''); // Clear input after sending
    // The file URI is cleared within the sendChatMessage thunk after successful use.
  }, [userInput, dispatch, chatState.currentFileUri, chatState.currentFileDisplayName, chatState.isFileContextApplied]);

  const handleFileUpload = useCallback(async (file: File) => {
    await dispatch(uploadFileForChat(file));
  }, [dispatch]);

  const clearUploadedFile = useCallback(() => {
    dispatch(setCurrentFile({ uri: null, displayName: null, contextApplied: false }));
  }, [dispatch]);

  // This function is now primarily for components that might still call applyTemplate directly from the hook.
  // The preferred way is for PromptTemplates to call the callback passed from ChatPage, which dispatches setInputPrompt.
  const applyTemplate = useCallback((template: string) => {
    dispatch(setInputPrompt(template)); // This will be picked up by the useEffect above
  }, [dispatch]);

  return {
    ...chatState,
    userInput,
    setUserInput,
    handleSendMessage,
    handleFileUpload,
    clearUploadedFile,
    applyTemplate,
  };
}; 