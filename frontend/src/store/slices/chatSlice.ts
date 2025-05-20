import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { v4 as uuidv4 } from 'uuid';
import { chatService } from '../../services/api';
import { ChatState, ChatMessageUI, ChatMessageAPI, ChatRequestAPI} from '../../types/index.ts';
import { toast } from 'react-toastify';

// Async thunk for sending a chat message
export const sendChatMessage = createAsyncThunk(
  'chat/sendMessage',
  async (payload: { message: string; fileUri?: string | null }, { getState, dispatch }) => {
    const { chat } = getState() as { chat: ChatState };
    const historyAPI: ChatMessageAPI[] = chat.messages
      .slice(0, -1) // Exclude the last user message as it's part of the current request
      .map(msg => ({
        role: msg.role === 'user' ? 'user' : 'model',
        content: msg.content,
      }));

    const requestPayload: ChatRequestAPI = {
      message: payload.message,
      file_uri: payload.fileUri || chat.currentFileUri,
      history: historyAPI,
    };

    try {
      const response = await chatService.sendChatMessage(requestPayload);
      dispatch(addMessage({
        id: uuidv4(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      }));
      // Clear the file URI after the message is successfully sent with it
      if (payload.fileUri || chat.currentFileUri) {
        dispatch(setCurrentFile({ uri: null, displayName: null, contextApplied: true }));
      }
      return response.response;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to send message';
      toast.error(errorMessage);
      // Add an error message to the chat or handle differently
      dispatch(addMessage({
        id: uuidv4(),
        role: 'assistant',
        content: `Error: ${errorMessage}`,
        timestamp: new Date(),
      }));
      throw new Error(errorMessage);
    }
  }
);

// Async thunk for uploading a PDF for chat
export const uploadFileForChat = createAsyncThunk(
  'chat/uploadFile',
  async (file: File, { dispatch, rejectWithValue }) => {
    try {
      dispatch(setUploadProgress(0)); // Reset progress
      const response = await chatService.uploadPdfForChat(file, (progressEvent) => {
        if (progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          dispatch(setUploadProgress(progress));
        }
      });
      dispatch(setCurrentFile({ uri: response.file_uri, displayName: response.display_name, contextApplied: false }));
      dispatch(setUploadProgress(100)); // Ensure progress is 100 on success
      toast.success(`File "${response.display_name}" uploaded successfully.`);
      return response;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to upload file';
      toast.error(errorMessage);
      dispatch(setUploadError(errorMessage));
      return rejectWithValue(errorMessage);
    }
  }
);

const initialState: ChatState = {
  messages: [],
  isLoading: false,
  error: null,
  currentFileUri: null,
  currentFileDisplayName: null,
  isFileContextApplied: false,
  isUploading: false,
  uploadError: null,
  uploadProgress: 0,
  inputPrompt: '', // For storing template-applied prompt
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessageUI>) => {
      state.messages.push(action.payload);
    },
    setMessages: (state, action: PayloadAction<ChatMessageUI[]>) => {
      state.messages = action.payload;
    },
    clearChat: (state) => {
      state.messages = [];
      state.error = null;
      state.isLoading = false;
      state.currentFileUri = null;
      state.currentFileDisplayName = null;
      state.isFileContextApplied = false;
      state.isUploading = false;
      state.uploadError = null;
      state.uploadProgress = 0;
      state.inputPrompt = '';
      toast.info("Chat cleared.");
    },
    setCurrentFile: (state, action: PayloadAction<{ uri: string | null; displayName: string | null; contextApplied?: boolean }>) => {
      state.currentFileUri = action.payload.uri;
      state.currentFileDisplayName = action.payload.displayName;
      if (action.payload.uri === null) { // If file is cleared
        state.isFileContextApplied = false;
      } else if (action.payload.contextApplied !== undefined) {
        state.isFileContextApplied = action.payload.contextApplied;
      }
      // When a new file is set, context is not yet applied to a message
      // It becomes "applied" once a message is sent using it.
      // If contextApplied is explicitly passed (e.g. true when clearing after send), use that.
      // Otherwise, if a new file is set, assume context is not yet applied.
      else if (action.payload.uri !== null) {
         state.isFileContextApplied = false;
      }
    },
    markFileContextApplied: (state) => {
      state.isFileContextApplied = true;
    },
    setUploading: (state, action: PayloadAction<boolean>) => {
      state.isUploading = action.payload;
      if (action.payload) state.uploadError = null; // Clear previous error on new upload
    },
    setUploadError: (state, action: PayloadAction<string | null>) => {
      state.uploadError = action.payload;
      state.isUploading = false;
      state.uploadProgress = 0;
    },
    setUploadProgress: (state, action: PayloadAction<number>) => {
      state.uploadProgress = action.payload;
    },
    setInputPrompt: (state, action: PayloadAction<string>) => {
      state.inputPrompt = action.payload;
    },
    clearInputPrompt: (state) => {
      state.inputPrompt = '';
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendChatMessage.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(sendChatMessage.fulfilled, (state) => {
        state.isLoading = false;
         // If a file was used for this message, mark its context as applied
        if (state.currentFileUri && !state.isFileContextApplied) {
            state.isFileContextApplied = true; 
        }
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to send message';
      })
      .addCase(uploadFileForChat.pending, (state) => {
        state.isUploading = true;
        state.uploadError = null;
        state.uploadProgress = 0;
      })
      .addCase(uploadFileForChat.fulfilled, (state) => {
        state.isUploading = false;
        state.uploadProgress = 100;
      })
      .addCase(uploadFileForChat.rejected, (state, action) => {
        state.isUploading = false;
        state.uploadError = action.payload as string;
        state.uploadProgress = 0;
        // Clear file info if upload failed critically
        state.currentFileUri = null;
        state.currentFileDisplayName = null;
        state.isFileContextApplied = false;
      });
  },
});

export const {
  addMessage,
  setMessages,
  clearChat,
  setCurrentFile,
  markFileContextApplied,
  setUploading,
  setUploadError,
  setUploadProgress,
  setInputPrompt,
  clearInputPrompt,
} = chatSlice.actions;

export default chatSlice.reducer; 