import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { RouterProvider } from 'react-router-dom';

import { AuthProvider } from './context/AuthContext';
import { router } from './router';
import './styles/index.css';

const BUILD_ID = __BUILD_ID__;
const BUILD_KEY = 'referencial_build_id';
const RELOAD_KEY = 'referencial_cache_bust';
const storedBuild = localStorage.getItem(BUILD_KEY);
const reloadAttempted = sessionStorage.getItem(RELOAD_KEY);

if (storedBuild && storedBuild !== BUILD_ID && !reloadAttempted) {
  sessionStorage.setItem(RELOAD_KEY, '1');
  const finalize = () => {
    localStorage.setItem(BUILD_KEY, BUILD_ID);
    window.location.reload();
  };

  if ('caches' in window) {
    caches
      .keys()
      .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
      .finally(finalize);
  } else {
    finalize();
  }
} else if (!storedBuild) {
  localStorage.setItem(BUILD_KEY, BUILD_ID);
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
      <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
    </QueryClientProvider>
  </React.StrictMode>,
);
