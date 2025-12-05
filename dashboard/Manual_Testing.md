# Manual Testing Checklist

## Prerequisites
- Backend running: `alphatrion server`
- Dashboard running: `cd dashboard && npm run dev`

## Test Cases

### Sidebar
- [ ] Alphatrion logo with gradient icon displays correctly
- [ ] Project selector dropdown works (below logo)

### Sidebar Navigation
- [ ] Experiments button highlights on `/experiments` and `/experiments/:id` pages
- [ ] Experiments button does NOT highlight on `/trials/:id` and `/runs/:id` pages
- [ ] Clicking Experiments button navigates back to Experiments Overview


### Experiments Page
- [ ] Overview tab: 3 metric cards (Total/Latest/Oldest Experiment)
- [ ] Overview tab: "Recent Experiments" table shows latest 5
- [ ] Overview tab: Cards clickable → navigate to experiment detail
- [ ] Overview tab: Recent table rows clickable → navigate to experiment detail
- [ ] List tab: Full-width table with all experiments
- [ ] List tab: Full experiment ID displayed
- [ ] List tab: Click ID → navigate to experiment detail
- [ ] Pill-style tabs with count badge

### Trials Page
- [ ] Trials nav enabled after selecting an experiment
- [ ] Overview + List tabs display correctly
- [ ] Click trial ID → navigate to trial detail

### Runs Page
- [ ] Runs nav enabled after selecting a trial
- [ ] Run ID clickable → navigate to run detail
- [ ] Run detail shows: ID, Trial ID, Experiment ID, Created, Metadata

### General UI
- [ ] Glassmorphism effect on sidebar (blur + transparency)
- [ ] Background gradient/pattern visible through content
- [ ] Hover effects on cards and table rows

