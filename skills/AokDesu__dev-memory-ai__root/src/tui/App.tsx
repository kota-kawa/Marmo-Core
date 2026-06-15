import React, { useState, useEffect } from 'react';
import { Box, useInput, useApp } from 'ink';
import { Header } from './components/Header.js';
import { Footer } from './components/Footer.js';
import { TabBar } from './components/TabBar.js';
import { ProjectSidebar } from './components/ProjectSidebar.js';
import { AskPane } from './components/AskPane.js';
import { SearchPane } from './components/SearchPane.js';
import { StatusPane } from './components/StatusPane.js';
import { WatchPane } from './components/WatchPane.js';
import { InitPane } from './components/InitPane.js';
import { useProject } from './hooks/useProject.js';

type Tab = 'ask' | 'search' | 'status' | 'watch' | 'init';
const TABS: Tab[] = ['ask', 'search', 'status', 'watch'];

export function App() {
  const { exit } = useApp();
  const { projects, loading, refetch } = useProject();
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('ask');
  const [sidebarFocused, setSidebarFocused] = useState(false);
  const [paneFocused, setPaneFocused] = useState(false);

  // Auto-select first project or go to init if none
  useEffect(() => {
    if (loading) return;
    if (projects.length === 0) {
      setActiveTab('init');
    } else if (!activeProjectId) {
      setActiveProjectId(projects[0].id);
    }
  }, [loading, projects.length]);

  // Global keyboard shortcuts (only when pane input is NOT active)
  useInput(
    (input, key) => {
      if (input === 'q' || (key.ctrl && input === 'c')) {
        exit();
        return;
      }
      // Tab cycles through tabs
      if (key.tab) {
        const idx = TABS.indexOf(activeTab as Tab);
        setActiveTab(TABS[(idx + 1) % TABS.length]);
        setPaneFocused(false);
        return;
      }
      // Left arrow → focus sidebar
      if (key.leftArrow) {
        setSidebarFocused(true);
        setPaneFocused(false);
        return;
      }
      // Right arrow → focus pane
      if (key.rightArrow) {
        setSidebarFocused(false);
        setPaneFocused(true);
        return;
      }
    },
    { isActive: !paneFocused }
  );

  const activeProject = projects.find((p) => p.id === activeProjectId) ?? null;

  const handleSelectProject = (id: string) => {
    setActiveProjectId(id);
    setSidebarFocused(false);
  };

  const handleInitNew = () => {
    setActiveTab('init');
    setSidebarFocused(false);
  };

  const handleInitComplete = async (projectId: string) => {
    await refetch();
    setActiveProjectId(projectId);
    setActiveTab('ask');
  };

  const handleReleasePaneFocus = () => {
    setPaneFocused(false);
  };

  return (
    <Box flexDirection="column" height={process.stdout.rows ?? 24}>
      {/* Header */}
      <Header
        projectName={activeProject?.name ?? null}
        projectStatus={activeProject?.status ?? null}
        chunkCount={null}
      />

      {/* Main area */}
      <Box flexGrow={1} flexDirection="row" gap={0}>
        {/* Sidebar */}
        <ProjectSidebar
          projects={projects}
          activeProjectId={activeProjectId}
          isFocused={sidebarFocused}
          onSelectProject={handleSelectProject}
          onInitNew={handleInitNew}
        />

        {/* Right panel */}
        <Box flexDirection="column" flexGrow={1}>
          <TabBar activeTab={activeTab} />

          {/* Active pane */}
          <Box flexGrow={1}>
            {activeTab === 'ask' && (
              <AskPane
                projectId={activeProjectId}
                isFocused={paneFocused}
                onReleaseFocus={handleReleasePaneFocus}
              />
            )}
            {activeTab === 'search' && (
              <SearchPane
                projectId={activeProjectId}
                isFocused={paneFocused}
                onReleaseFocus={handleReleasePaneFocus}
              />
            )}
            {activeTab === 'status' && (
              <StatusPane project={activeProject} />
            )}
            {activeTab === 'watch' && (
              <WatchPane project={activeProject} />
            )}
            {activeTab === 'init' && (
              <InitPane onComplete={handleInitComplete} />
            )}
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Footer
        sidebarFocused={sidebarFocused}
        activeTab={activeTab}
        inputFocused={paneFocused}
      />
    </Box>
  );
}
