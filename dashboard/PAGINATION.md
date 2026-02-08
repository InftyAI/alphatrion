# Pagination Implementation

## Overview

All list views (projects, experiments, runs) now support pagination to improve performance and usability when dealing with large datasets.

## Features

✅ **Projects List** - Paginated with 10 items per page
✅ **Experiments List** - Paginated in project detail view
✅ **Runs List** - Paginated in experiment detail view
✅ **Reusable Component** - Single pagination component used everywhere
✅ **Page State** - Page selection persists during navigation
✅ **Smooth Scrolling** - Auto-scroll to top on page change
✅ **Smart Display** - Only shows when there are enough items

## Configuration

### Page Sizes

```typescript
const PAGE_SIZE = 10; // Default page size for all lists
```

Currently using 10 items per page for:
- Projects
- Experiments
- Runs

### API Pagination

Backend uses 0-based page indexing:
```typescript
// Frontend: Page 1
// Backend: page=0

// Frontend: Page 2
// Backend: page=1
```

## Pagination Component

Located at: `src/components/ui/pagination.tsx`

### Usage

```typescript
<Pagination
  currentPage={currentPage}          // Current page (1-based)
  totalPages={totalPages}            // Total number of pages
  pageSize={PAGE_SIZE}               // Items per page
  totalItems={totalItems}            // Optional: Total item count
  onPageChange={(page) => {          // Page change handler
    setCurrentPage(page);
    window.scrollTo({ top: 0 });
  }}
/>
```

### Features

**Navigation:**
- Previous/Next buttons
- Direct page number buttons
- Ellipsis (...) for large page counts
- Disabled state for first/last pages

**Display:**
- Shows current range (e.g., "Showing 1 to 10 of 45 results")
- Smart page number display (shows pages around current)
- Responsive layout

**Behavior:**
- Smooth page transitions
- Auto-scroll to top on page change
- Keyboard accessible

## Implementation Details

### Projects Page

```typescript
const [currentPage, setCurrentPage] = useState(1);

const { data: projects } = useProjects(selectedTeamId || '', {
  page: currentPage - 1,  // Convert to 0-based
  pageSize: PAGE_SIZE,
  enabled: !!selectedTeamId,
});
```

### Experiments List (in Project Detail)

```typescript
const [currentPage, setCurrentPage] = useState(1);

const { data: experiments } = useExperiments(projectId, {
  page: currentPage - 1,
  pageSize: PAGE_SIZE,
  enabled: !!projectId,
});
```

### Runs List (in Experiment Detail)

```typescript
const [currentPage, setCurrentPage] = useState(1);

const { data: runs } = useRuns(experimentId, {
  page: currentPage - 1,
  pageSize: PAGE_SIZE,
});
```

## Hook Updates

All hooks now accept options for pagination:

### useProjects
```typescript
useProjects(teamId: string, options?: {
  page?: number;
  pageSize?: number;
  enabled?: boolean;
})
```

### useExperiments
```typescript
useExperiments(projectId: string, options?: {
  page?: number;
  pageSize?: number;
  enabled?: boolean;
})
```

### useRuns
```typescript
useRuns(experimentId: string, options?: {
  page?: number;
  pageSize?: number;
  enabled?: boolean;
})
```

## GraphQL Queries

Backend queries support pagination:

```graphql
query ListProjects($teamId: String!, $page: Int, $pageSize: Int) {
  projects(teamId: $teamId, page: $page, pageSize: $pageSize) {
    id
    name
    # ...
  }
}
```

## Visual Design

### Pagination Bar Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Showing 11 to 20 of 45 results    [<] [1] ... [3] [4] [5] [>] │
└─────────────────────────────────────────────────────────────┘
```

### Page Number Display Logic

- **1-7 pages:** Show all page numbers
- **8+ pages:** Show ellipsis with smart page selection
  - Always show first page
  - Show current page ± 1
  - Always show last page
  - Ellipsis fills the gaps

Examples:
```
Total: 5 pages
Display: [1] [2] [3] [4] [5]

Total: 15 pages, Current: 1
Display: [1] [2] [3] ... [15]

Total: 15 pages, Current: 8
Display: [1] ... [7] [8] [9] ... [15]

Total: 15 pages, Current: 15
Display: [1] ... [13] [14] [15]
```

## Styling

Uses Tailwind CSS with shadcn/ui design system:

```typescript
// Active page
className="bg-primary text-primary-foreground"

// Inactive page
className="bg-background text-foreground"

// Disabled button
disabled={currentPage === 1}
```

## Performance

### Benefits

1. **Reduced Data Transfer** - Only fetch 10 items instead of all
2. **Faster Rendering** - Fewer DOM elements to render
3. **Better UX** - Easier to navigate and find items
4. **Scalable** - Works with thousands of items

### Optimization

- Pagination only appears when needed (>= PAGE_SIZE items)
- Page state resets when switching teams
- Queries are cached by React Query
- Polling continues to work with pagination

## User Experience

### Navigation Flow

1. **Landing on list page** - Shows page 1
2. **Click page number** - Loads that page
3. **Click Next** - Advances to next page
4. **Auto-scroll** - Page scrolls to top for easy viewing
5. **Switch team** - Pagination resets to page 1

### Empty States

- **No items:** Shows "No X found" message
- **Last page partial:** Shows remaining items
- **Single page:** No pagination shown

## Testing

### Test Pagination

1. **Create 15+ projects:**
```python
for i in range(15):
    project = proj.Project.setup(name=f"Test Project {i+1}")
```

2. **Open projects page:**
- Should see first 10 projects
- Pagination bar at bottom
- Page numbers 1, 2, etc.

3. **Click page 2:**
- Should see projects 11-15
- Previous button enabled
- Current page highlighted

### Test with Different Counts

- **1-9 items:** No pagination
- **10 items:** No pagination (edge case)
- **11+ items:** Pagination appears
- **100+ items:** Ellipsis in page numbers

## Limitations

### Current Implementation

1. **Total Count Unknown** - Backend doesn't return total count
   - Solution: Shows approximate page count
   - Shows pagination if PAGE_SIZE items returned

2. **Last Page Detection** - Can't know if there are more pages
   - Solution: Always show "next" if full page returned
   - User sees empty page if they go too far

3. **Page Size Fixed** - Can't change items per page
   - Future: Add page size selector (10, 25, 50, 100)

## Future Enhancements

Potential improvements:

- [ ] Add total count to GraphQL queries
- [ ] Page size selector dropdown
- [ ] "Jump to page" input field
- [ ] Keyboard shortcuts (← → for prev/next)
- [ ] URL parameters for page state
- [ ] "Load more" infinite scroll option
- [ ] Remember page per list type
- [ ] Export all pages as CSV

## Files Modified

### New Files
- `src/components/ui/pagination.tsx` - Pagination component

### Modified Files
- `src/pages/projects/index.tsx` - Added pagination
- `src/pages/projects/[id].tsx` - Added pagination for experiments
- `src/pages/experiments/[id].tsx` - Added pagination for runs
- `src/hooks/use-projects.ts` - Added pagination options
- `src/hooks/use-experiments.ts` - Added pagination options
- `src/hooks/use-runs.ts` - Added pagination options

## API Reference

### Pagination Component Props

```typescript
interface PaginationProps {
  currentPage: number;        // Current page (1-based)
  totalPages: number;         // Total number of pages
  onPageChange: (page: number) => void;  // Page change callback
  pageSize: number;           // Items per page
  totalItems?: number;        // Optional total item count
  className?: string;         // Optional CSS classes
}
```

### Hook Options

```typescript
interface PaginationOptions {
  page?: number;              // Page number (0-based for backend)
  pageSize?: number;          // Items per page
  enabled?: boolean;          // Whether to fetch data
}
```

## Troubleshooting

### Pagination not showing

**Check:**
- Do you have > PAGE_SIZE items?
- Is the pagination component rendered?
- Check browser console for errors

### Wrong page displayed

**Debug:**
```typescript
console.log('Current page:', currentPage);
console.log('API page:', currentPage - 1);
console.log('Items:', data?.length);
```

### Page state not persisting

**Note:** Page state resets when:
- Switching teams
- Navigating away and back
- Refreshing page

**Future:** Add URL parameters to persist state

## Related Documentation

- Team Switcher: `TEAM_SWITCHER.md`
- Dashboard Setup: `DASHBOARD_SETUP.md`
- Debugging: `DEBUGGING_EXPERIMENTS.md`
