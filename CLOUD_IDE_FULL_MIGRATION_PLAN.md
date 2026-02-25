# Cloud IDE - Full Trial Page Migration Plan

To implement the complete trial detail page UI from the forked project as the Cloud IDE, we need to migrate a significant number of components and hooks.

## Current Status

✅ **Completed:**
- IDE served at `/api/plugins/cloud-ide/ide`
- Sidebar opens IDE in new tab
- Basic IDE with file browser, code editor, terminal, chat

❌ **Missing (from forked trial page):**
- Content evolution chart
- Lineage history and tree visualizations
- Content comparison panel
- Metrics tree view
- Repository browser integration
- Trial/experiment-specific data hooks

## Components to Migrate

### 1. Content Evolution Components
**From:** `/Users/kerthcet/Workspaces/hiverge/alphatrion/dashboard/src/components/content/`

Files needed:
- `content-evolution-chart.tsx` (75KB, 2000+ lines) - Main scatter plot with evolution visualization
- `lineage-history.tsx` - Ancestor/descendant navigation
- `lineage-tree.tsx` - Visual tree representation
- `content-comparison-panel.tsx` - Side-by-side code comparison
- `content-browser.tsx` - Navigate through content snapshots
- `code-viewer.tsx` - Enhanced code viewer with highlighting

### 2. Chart Components
**From:** `/Users/kerthcet/Workspaces/hiverge/alphatrion/dashboard/src/components/charts/`

Files needed:
- `metrics-tree.tsx` - Hierarchical metrics display
- Supporting chart utilities

### 3. Repository Browser
**From:** `/Users/kerthcet/Workspaces/hiverge/alphatrion/dashboard/src/components/repo/`

Already copied but need integration:
- `file-tree.tsx`
- `file-viewer.tsx`
- `repo-browser.tsx`

### 4. Chat Component
**From:** `/Users/kerthcet/Workspaces/hiverge/alphatrion/dashboard/src/components/chat/`

Already copied but need integration:
- `ChatInline.tsx`
- `ChatInput.tsx`
- `ChatMessage.tsx`
- `ChatPanel.tsx`

## Hooks to Migrate

### 1. Content Snapshot Hooks
**From:** `/Users/kerthcet/Workspaces/hiverge/alphatrion/dashboard/src/hooks/`

Files:
- `use-content-snapshots.ts` - Fetch and manage content snapshots
- `use-trial-detail.ts` - Get trial information → **Needs adaptation to experiments**
- `use-repo-browser.ts` - Repository file browsing
- `use-trial-metrics.ts` - Metrics for trial → **Needs adaptation to experiments**

## Backend Requirements

### 1. Content Snapshots API

Need to add these endpoints (if not exists):
```python
GET /api/experiments/{id}/content-snapshots
GET /api/content-snapshots/{id}
POST /api/experiments/{id}/content-snapshots
```

### 2. Repository API

For browsing code files in experiment context:
```python
GET /api/experiments/{id}/repo/tree
GET /api/experiments/{id}/repo/file?path=...
```

## Data Model Considerations

### Trial → Experiment Mapping

**Old structure (forked project):**
```
Project → Experiment → Trial → Run
```

**New structure (current project):**
```
Team → Project → Experiment → Run
```

**Impact:**
- All `trial_id` references need to change to `experiment_id`
- Content snapshots table needs `experiment_id` instead of `trial_id`
- Metrics queries need updating
- UI state management needs adjustment

## Migration Complexity

### Phase 1: Basic IDE (Current) ✅
- File browser
- Code editor
- Terminal
- Simple chat placeholder

**Effort:** COMPLETE

### Phase 2: Repository Integration
- Full repo file tree
- Code syntax highlighting
- File navigation
- File editing capabilities

**Effort:** ~2-4 hours

### Phase 3: Content Evolution
- Content snapshots system
- Evolution chart visualization
- Lineage tracking
- Comparison tools

**Effort:** ~8-12 hours (complex visualization logic)

### Phase 4: Metrics & Analysis
- Metrics tree view
- Data aggregation
- Time-series charts
- Performance graphs

**Effort:** ~4-6 hours

### Phase 5: Integration & Polish
- Connect all components
- State management
- Loading states
- Error handling
- Responsive layout

**Effort:** ~4-6 hours

**Total Estimated Effort:** ~18-28 hours

## Recommended Approach

### Option A: Incremental Migration (Recommended)

1. ✅ **Week 1:** Basic IDE with file browser, editor, terminal (DONE)
2. **Week 2:** Add repository browser with full file tree
3. **Week 3:** Implement content snapshots and basic visualization
4. **Week 4:** Add evolution chart and lineage features
5. **Week 5:** Integrate metrics and polish

**Pros:**
- Steady progress
- Testing at each stage
- Can use IDE immediately
- Lower risk

**Cons:**
- Takes longer to get full features
- Need to maintain compatibility during migration

### Option B: Full Migration (All at Once)

Copy entire trial detail page and all dependencies, adapt in one go.

**Pros:**
- Get all features at once
- No incremental integration issues

**Cons:**
- High risk
- Longer development time before anything works
- Harder to debug
- May break existing functionality

### Option C: Hybrid - Core Features Only

Implement essential IDE features, skip advanced visualizations:
- File browser ✅
- Code editor ✅
- Terminal ✅
- Chat ✅
- Repository browser (full) 🔄
- Content snapshots (basic list view) 🔄
- **Skip:** Evolution charts, lineage tree, comparison panel

**Pros:**
- Faster to implement
- Covers 80% of use cases
- Can add visualizations later

**Cons:**
- Missing some powerful analysis features

## Current State

The Cloud IDE is now accessible at:
- **URL:** `/api/plugins/cloud-ide/ide`
- **Opens:** In new browser tab from sidebar
- **Features:** File browser, code editor, terminal, chat placeholder

## Next Steps (Recommendation)

**Immediate (This Sprint):**
1. ✅ Fix backend restart issue (already done)
2. ✅ Verify Cloud IDE appears in sidebar
3. ✅ Test opening in new tab
4. Add experiment context to IDE (pass experiment ID via URL)

**Short-term (Next Sprint):**
1. Enhance file browser with full repo tree
2. Add real file editing capabilities
3. Implement file save/create/delete
4. Add syntax highlighting for more languages

**Medium-term (Following Sprint):**
1. Add content snapshots basic UI
2. Implement snapshot creation
3. Add snapshot browsing
4. Simple diff viewer

**Long-term (Future Sprints):**
1. Evolution chart visualization
2. Lineage tree
3. Metrics integration
4. Advanced analysis tools

## Alternative: Simplified Trial View

Instead of migrating the entire complex trial page, create a simplified "Experiment IDE" view:

**Layout:**
```
┌─────────────────────────────────────────┐
│ Experiment: <name>          [Save] [Run]│
├──────────┬───────────────────────────────┤
│ Files    │ Code Editor                   │
│          │                               │
│ - src/   │ 1  def train():              │
│   main.py│ 2    model = Model()         │
│ - tests/ │ 3    ...                     │
│          │                               │
├──────────┴───────────────────────────────┤
│ Terminal                                 │
│ $ python main.py                         │
│ Training started...                      │
└──────────────────────────────────────────┘
```

**Benefits:**
- Clean, focused interface
- Faster implementation
- Easier to maintain
- Better performance

**Compared to full trial page:**
- ❌ No evolution chart
- ❌ No lineage tree
- ❌ No comparison panel
- ✅ Cleaner interface
- ✅ Faster loading
- ✅ Easier to use

## Decision Required

Please decide which approach you prefer:

1. **Continue with current simple IDE** (file browser, editor, terminal, chat)
2. **Add repository browser next** (enhanced file navigation)
3. **Full migration** of trial page with all visualization features
4. **Hybrid approach** (core features, skip visualizations)

The current implementation is functional and provides a good foundation. Adding the full trial page features is a significant undertaking that requires careful planning and incremental development.

## Files Inventory

**Currently in dashboard/src/components/ide/:**
- ✅ `repo/` - File tree components (partial)
- ✅ `editor/` - Monaco editor (basic)
- ✅ `terminal/` - Terminal panel (basic)
- ✅ `chat/` - Chat components (copied, needs integration)
- ❌ `content/` - NOT copied yet (evolution, lineage, comparison)
- ❌ `charts/` - NOT copied yet (metrics visualization)

**Currently in dashboard/src/hooks/ide/:**
- ✅ `use-repo-browser.ts` (copied)
- ✅ `use-content-snapshots.ts` (copied)
- ❌ Many other hooks NOT copied yet

**Status:** ~30% of full trial page migrated
