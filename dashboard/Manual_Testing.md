# Manual Testing Checklist

## Prerequisites

- Backend running: `alphatrion server`
- Dashboard running: `cd dashboard && npm run dev`

## Test Cases

### Projects Page

- [ ] Page loads, auto-redirects to first project's experiments on initial visit
- [ ] Click "Projects" in sidebar shows all projects
- [ ] Full project ID displayed in first column
- [ ] Click project ID navigates to that project's experiments

### Experiments Page

- [ ] Overview tab shows total count, latest and oldest experiment
- [ ] List tab shows experiments with full ID in first column
- [ ] Click experiment ID navigates to experiment detail

### Experiment Detail

- [ ] Breadcrumb navigation works (Projects / Experiments / Experiment Name)
- [ ] Experiment info displays correctly (full ID, Project ID, Created, Updated)
- [ ] Metadata displays if available
- [ ] Trials list displays with full ID in first column
- [ ] Click trial ID navigates to trial detail

### Trial Detail

- [ ] Breadcrumb navigation works
- [ ] Trial info displays (full ID, Duration, Status, Created, Updated)
- [ ] Parameters and Metadata display if available
- [ ] Metrics chart renders with multiple metrics (accuracy, fitness, etc.)
- [ ] Runs list displays with full ID in first column

### Known Limitations

- Sidebar only shows "Projects" - navigate to Experiments via project selection
- Run detail page not yet implemented