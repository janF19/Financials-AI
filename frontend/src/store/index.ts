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

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth'], // Only persist auth state
};

const rootReducer = combineReducers({
  auth: authReducer,
  reports: reportReducer,
  dashboard: dashboardReducer,
  upload: uploadReducer,
  search: searchReducer,
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
        ],
        ignoredPaths: ['search.error', 'search.valuationError'],
      },
    }),
});

export const persistor = persistStore(store);

export type AppDispatch = typeof store.dispatch;