# Cloud IDE - Project and Experiment Selector

Added UI controls to select projects and experiments in the Cloud IDE page, allowing users to choose which experiment to work with.

## Changes Made

### 1. Added Selector UI

Added a header bar at the top of the Cloud IDE page with:
- **Project Selector**: Dropdown to choose from available projects
- **Experiment Selector**: Dropdown to choose experiments within the selected project
- **Status Display**: Shows the current experiment's status (COMPLETED, RUNNING, FAILED, etc.)

### 2. State Management

**New state variables:**
```typescript
const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);
```

**Data fetching:**
- Uses `useProjects()` hook to fetch all projects for the current team
- Uses `useExperiments(projectId)` hook to fetch experiments for the selected project
- Auto-selects the first project on load
- Resets experiment selection when project changes

### 3. Updated Component Structure

**Header Section:**
```tsx
<div className="border-b bg-background px-4 py-3 flex items-center gap-4">
  {/* Project Selector */}
  <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
    {/* ... */}
  </Select>

  {/* Experiment Selector */}
  <Select value={selectedExperimentId} onValueChange={setSelectedExperimentId}>
    {/* ... */}
  </Select>

  {/* Status Display */}
  <div className="ml-auto">Status: {experiment.status}</div>
</div>
```

**Content Section:**
- Shows placeholder message when no project/experiment is selected
- Shows loading state while fetching experiment data
- Shows error message if experiment fails to load
- Renders full IDE interface once experiment is loaded

### 4. Updated References

Changed all `experimentId` references from URL params to `selectedExperimentId` state:
- Content snapshots: `useContentSnapshotsSummary(selectedExperimentId)`
- Repository browser: `useRepoFileTree(selectedExperimentId)`
- Metrics tree: `<MetricsTree experimentId={selectedExperimentId} />`
- Chat panel: `<ChatInline experimentId={selectedExperimentId} />`

## User Flow

1. **Open Cloud IDE**: Click "Cloud IDE" in sidebar → Opens `/api/plugins/cloud-ide/ide` in new tab
2. **Select Project**: Choose a project from the dropdown (first project auto-selected)
3. **Select Experiment**: Choose an experiment within that project
4. **View IDE**: Full IDE interface loads with:
   - Evolution chart
   - Content snapshots
   - Repository browser
   - Code viewer
   - Lineage history
   - Metrics visualization

## UI States

### No Selection
```
┌─────────────────────────────────────────┐
│ Project: [Select...]  Experiment: [...]│
├─────────────────────────────────────────┤
│                                         │
│  Please select a project and            │
│  experiment to get started.             │
│                                         │
└─────────────────────────────────────────┘
```

### Loading
```
┌─────────────────────────────────────────┐
│ Project: [MyProject]  Experiment: [123] │
├─────────────────────────────────────────┤
│                                         │
│        ⏳ Loading experiment...          │
│                                         │
└─────────────────────────────────────────┘
```

### Loaded
```
┌─────────────────────────────────────────────────────────┐
│ Project: [MyProject]  Experiment: [123]  Status: RUNNING│
├──────────┬───────────────────────────┬──────────────────┤
│ Files    │ Code Viewer               │ Evolution Chart  │
│          │                           │                  │
│ - src/   │ def train():             │   ●              │
│   main.py│   model = Model()        │     ●   ●        │
│ - tests/ │   ...                    │       ●          │
│          │                           │                  │
├──────────┴───────────────────────────┴──────────────────┤
│ Evolution History                                       │
│ ○ Seed → ● v1 → ● v2 → ● v3 (current)                 │
└─────────────────────────────────────────────────────────┘
```

## Benefits

1. **No URL dependency**: Users don't need to know experiment IDs or URLs
2. **Easy switching**: Can quickly switch between experiments without leaving the IDE
3. **Context awareness**: Shows project and experiment names clearly
4. **Status visibility**: Current experiment status is always visible
5. **Progressive disclosure**: Only shows experiment list after project is selected

## Technical Notes

- Selectors use shadcn/ui `Select` component
- Experiment list is automatically filtered by selected project
- Status display uses color coding (green=completed, blue=running, red=failed)
- All experiment-related data fetching is disabled until an experiment is selected
- Auto-polling continues to work for running experiments

## Future Enhancements

1. **Search/Filter**: Add search boxes to filter large lists of projects/experiments
2. **Recent Experiments**: Show a list of recently viewed experiments
3. **Favorites**: Allow users to star/favorite experiments for quick access
4. **URL Sync**: Optionally sync selections to URL query params for bookmarking
5. **Keyboard Navigation**: Add keyboard shortcuts (Ctrl+P for project, Ctrl+E for experiment)
