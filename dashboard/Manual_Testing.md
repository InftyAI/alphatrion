# Manual Testing Checklist

## Prerequisites
- Backend running: `uv run alphatrion server --host 127.0.0.1`
- Frontend running: `npm run dev`

## Test Cases

### Projects Page
- [ ] Page loads without error
- [ ] Projects list displays
- [ ] "View Experiments" link works

### Experiments Page
- [ ] Overview tab shows total count
- [ ] List tab shows experiments
- [ ] Clicking experiment name navigates to detail

### Experiment Detail
- [ ] Breadcrumb navigation works
- [ ] Experiment info displays correctly
- [ ] Trials list displays
- [ ] Clicking trial name navigates to detail

### Trial Detail
- [ ] Trial info displays (ID, Duration, Status)
- [ ] Parameters and Metadata display
- [ ] Metrics chart renders
- [ ] Runs list displays

### Runs
- Component under construction