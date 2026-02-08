# Team Switcher - Multi-Tenant Isolation

## Overview

The team switcher provides multi-tenant isolation, allowing users to switch between different teams and view only the data associated with the selected team.

## Features

✅ **Dropdown in Header** - Team selector in the top-right corner
✅ **Persistent Selection** - Selected team is saved to localStorage
✅ **Auto-Selection** - Automatically selects first team on initial load
✅ **Real-Time Updates** - All data updates when team is changed
✅ **Visual Feedback** - Shows current team name and description
✅ **Multi-Tenant** - Complete isolation between teams

## How It Works

### Architecture

```
TeamProvider (Context)
    ├─ Stores selectedTeamId
    ├─ Persists to localStorage
    └─ Provides to all components

TeamSwitcher (Component)
    ├─ Fetches all teams
    ├─ Shows dropdown with team list
    └─ Updates context on selection

Pages/Hooks
    └─ Read selectedTeamId from context
    └─ Fetch data for selected team only
```

### Data Flow

1. **User opens dashboard** → TeamProvider loads team from localStorage
2. **TeamSwitcher component** → Fetches all teams user has access to
3. **User selects team** → Updates context and saves to localStorage
4. **All pages react** → Fetch data for newly selected team
5. **Page refresh** → Selected team is restored from localStorage

## Usage

### For Users

**Switching Teams:**

1. Look for the team dropdown in the top-right corner of the header
2. Click on the dropdown to see all available teams
3. Select the team you want to view
4. All data (projects, experiments, runs) will update automatically

**Current Team Display:**

The dropdown shows:
- 🏢 Team icon
- Team name
- Team description (if available)
- Checkmark on selected team

### For Developers

**Accessing Selected Team in Components:**

```typescript
import { useTeamContext } from '../../context/team-context';

function MyComponent() {
  const { selectedTeamId, setSelectedTeamId } = useTeamContext();

  // Use selectedTeamId to fetch data
  const { data } = useProjects(selectedTeamId);

  return <div>Current team: {selectedTeamId}</div>;
}
```

**In Hooks:**

Most hooks now accept an optional `enabled` parameter that checks for valid team ID:

```typescript
const { data: projects } = useProjects(selectedTeamId || '', {
  enabled: !!selectedTeamId,
});
```

## Files Modified

### New Files

1. **`context/team-context.tsx`** - Team context provider
   - Manages selected team state
   - Persists to localStorage
   - Provides team selection methods

2. **`components/layout/team-switcher.tsx`** - Team switcher component
   - Dropdown UI for team selection
   - Auto-selects first team
   - Shows team list with descriptions

### Modified Files

3. **`main.tsx`** - Wrapped app with TeamProvider

4. **`components/layout/header.tsx`** - Added TeamSwitcher to header
   - Positioned in top-right corner
   - Aligned with breadcrumbs

5. **`pages/projects/index.tsx`** - Uses selectedTeamId from context
   - Shows message if no team selected
   - Fetches projects for selected team only

6. **`pages/dashboard/index.tsx`** - Uses selectedTeamId from context
   - Shows stats for selected team
   - Lists projects from selected team

## Multi-Tenant Isolation

### How Isolation Works

Each team has a unique UUID. When a team is selected:

1. **Projects** - Only projects belonging to that team are fetched
2. **Experiments** - Only experiments in team's projects are shown
3. **Runs** - Only runs from team's experiments are displayed
4. **Metrics** - Only metrics from team's runs are visible
5. **Artifacts** - Only artifacts in team's namespace are accessible

### Data Hierarchy

```
Team (UUID)
  └─ Projects
      └─ Experiments
          └─ Runs
              └─ Metrics
```

When you switch teams, you switch the entire data tree.

### Security Considerations

**Frontend:**
- Team selection is stored in browser localStorage
- Team ID is sent with every GraphQL query
- Frontend only shows data for selected team

**Backend:**
- Backend validates team membership
- Database queries filter by team_id
- Users can only access teams they're authorized for

⚠️ **Note:** The current implementation assumes all teams are accessible. In production, you should add proper authentication and team membership validation on the backend.

## Testing

### Test with Multiple Teams

1. **Create multiple teams:**

```python
import uuid
import alphatrion
from alphatrion.project import project as proj

# Team 1
team1_id = uuid.uuid4()
user_id = uuid.uuid4()
alphatrion.init(team_id=team1_id, user_id=user_id)

project1 = proj.Project.setup(name="Team 1 Project")
print(f"Team 1 ID: {team1_id}")

# Team 2
team2_id = uuid.uuid4()
alphatrion.init(team_id=team2_id, user_id=user_id)

project2 = proj.Project.setup(name="Team 2 Project")
print(f"Team 2 ID: {team2_id}")
```

2. **Test in dashboard:**
   - Open dashboard
   - You should see 2 teams in dropdown
   - Switch between them
   - Verify projects list changes

### Verify Isolation

1. Select Team 1 → Note the projects shown
2. Select Team 2 → Projects should be completely different
3. Check localStorage → `alphatrion_selected_team` should update
4. Refresh page → Selected team should persist

## Troubleshooting

### Team switcher not showing

**Check:**
- Are there teams in the database?
- Run: `python scripts/verify_data.py`
- Look for teams in output

### Wrong team selected

**Clear localStorage:**
```javascript
// In browser console
localStorage.removeItem('alphatrion_selected_team');
location.reload();
```

### Data not updating when switching teams

**Check:**
1. Browser console for errors
2. Network tab - verify GraphQL queries include correct teamId
3. Backend logs - check queries are using team_id filter

## Future Enhancements

Potential improvements:

- [ ] Team search/filter (when you have many teams)
- [ ] Recently used teams
- [ ] Team favorites/bookmarks
- [ ] Team metadata display (member count, etc.)
- [ ] Team switcher keyboard shortcuts (Cmd+K)
- [ ] Team-based permissions and roles
- [ ] Invite team members
- [ ] Team settings page

## API Reference

### TeamContext

```typescript
interface TeamContextValue {
  selectedTeamId: string | null;  // Currently selected team UUID
  setSelectedTeamId: (teamId: string) => void;  // Change selected team
}
```

### useTeamContext Hook

```typescript
import { useTeamContext } from './context/team-context';

const { selectedTeamId, setSelectedTeamId } = useTeamContext();

// Get current team
console.log('Current team:', selectedTeamId);

// Change team
setSelectedTeamId('new-team-uuid');
```

### localStorage Key

```typescript
const TEAM_STORAGE_KEY = 'alphatrion_selected_team';
```

## Related Files

- Context: `src/context/team-context.tsx`
- Component: `src/components/layout/team-switcher.tsx`
- Hook: `src/hooks/use-teams.ts`
- Layout: `src/components/layout/header.tsx`
