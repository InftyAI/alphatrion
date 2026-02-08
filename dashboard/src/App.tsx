import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/layout/layout';
import { DashboardPage } from './pages/dashboard';
import { ProjectsPage } from './pages/projects';
import { ProjectDetailPage } from './pages/projects/[id]';
import { ExperimentsPage } from './pages/experiments';
import { ExperimentDetailPage } from './pages/experiments/[id]';
import { ExperimentComparePage } from './pages/experiments/compare';
import { RunsPage } from './pages/runs';
import { RunDetailPage } from './pages/runs/[id]';
import { ArtifactsPage } from './pages/artifacts';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects">
          <Route index element={<ProjectsPage />} />
          <Route path=":id" element={<ProjectDetailPage />} />
        </Route>
        <Route path="experiments">
          <Route index element={<ExperimentsPage />} />
          <Route path=":id" element={<ExperimentDetailPage />} />
          <Route path="compare" element={<ExperimentComparePage />} />
        </Route>
        <Route path="runs">
          <Route index element={<RunsPage />} />
          <Route path=":id" element={<RunDetailPage />} />
        </Route>
        <Route path="artifacts" element={<ArtifactsPage />} />
      </Route>
    </Routes>
  );
}

export default App;
