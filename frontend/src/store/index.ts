// src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { combineReducers } from 'redux';
import { fetchCompanies, triggerValuation } from './slices/searchSlice';

import authReducer from './slices/authSlice';
import reportReducer from './slices/reportSlice';
import dashboardReducer from './slices/dashboardSlice';
import uploadReducer from './slices/uploadSlice';
import searchReducer from './slices/searchSlice';
import companyInfoReducer from './slices/companyInfoSlice';
import chatReducer from './slices/chatSlice';

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth', 'chat'],
};

const rootReducer = combineReducers({
  auth: authReducer,
  reports: reportReducer,
  dashboard: dashboardReducer,
  upload: uploadReducer,
  search: searchReducer,
  companyInfo: companyInfoReducer,
  chat: chatReducer,
});

export type RootState = ReturnType<typeof rootReducer>;

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'persist/PERSIST',
          fetchCompanies.rejected.type,
          triggerValuation.rejected.type,
          'chat/sendMessage/rejected',
          'chat/uploadFile/rejected',
          'chat/addMessage',
        ],
        ignoredPaths: [
          'search.error',
          'search.valuationError',
          'chat.error',
          'chat.uploadError',
          'chat.messages',
        ],
        ignoredActionPaths: ['payload.timestamp', 'meta.arg', 'payload.headers'],
      },
    }),
});

export const persistor = persistStore(store);

export type AppDispatch = typeof store.dispatch;