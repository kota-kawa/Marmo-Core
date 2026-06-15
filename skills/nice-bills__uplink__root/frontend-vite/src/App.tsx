/**
 * App — global ambient video + smooth route transitions
 */

import { useLocation, useRoutes } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Navbar } from './components/Navbar';
import { AmbientBackground } from './components/AmbientBackground';
import { PageTransition } from './components/PageTransition';
import { ErrorBoundary } from './components/ErrorBoundary';
import { HomePage } from './pages/HomePage';
import { CampaignsPage } from './pages/CampaignsPage';
import { CampaignDetailPage } from './pages/CampaignDetailPage';
import { LeaderboardPage } from './pages/LeaderboardPage';
import { CreateCampaignPage } from './pages/CreateCampaignPage';
import { UserProfilePage } from './pages/UserProfilePage';
import { EmbedPage } from './pages/EmbedPage';
import '@rainbow-me/rainbowkit/styles.css';

const routes = [
  { path: '/', element: <HomePage /> },
  { path: '/campaigns', element: <CampaignsPage /> },
  { path: '/campaign/:id', element: <CampaignDetailPage /> },
  { path: '/leaderboard', element: <LeaderboardPage /> },
  { path: '/create', element: <CreateCampaignPage /> },
  { path: '/profile', element: <UserProfilePage /> },
  { path: '/embed/:id', element: <EmbedPage /> },
];

function App() {
  const location = useLocation();
  const element = useRoutes(routes);

  return (
    <ErrorBoundary>
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <AmbientBackground />
      <div className="relative z-10 min-h-screen">
        <Navbar />
        <main id="main-content">
          <AnimatePresence mode="wait">
            <PageTransition key={location.pathname}>{element}</PageTransition>
          </AnimatePresence>
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
