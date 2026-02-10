import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { queryClient } from './lib/query-client';
import { TeamProvider } from './context/team-context';
import App from './App';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TeamProvider>
          <App />
        </TeamProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
