# Debugging: Cannot Browse Experiments

## Quick Checks

### 1. Check Browser Console

Open the browser developer console (F12) and look for errors:

```
Projects page: http://localhost:8000/projects
Click a project → Check console for errors
```

Look for:
- ❌ GraphQL errors
- ❌ Network errors (failed to fetch)
- ❌ UUID format errors

### 2. Verify Test Data Was Created

Check if experiments exist in the database:

```python
import os
os.environ['ALPHATRION_METADATA_DB_URL'] = 'your_db_url'

from alphatrion.storage.sqlstore import SQLStore
db = SQLStore(os.environ['ALPHATRION_METADATA_DB_URL'])

# List all projects
projects = db.list_projects(team_id='<your-team-uuid>')
print(f"Found {len(projects)} projects")

for project in projects:
    print(f"\nProject: {project.name} (ID: {project.uuid})")

    # List experiments in this project
    experiments = db.list_exps_by_project_id(project_id=project.uuid)
    print(f"  Experiments: {len(experiments)}")

    for exp in experiments:
        print(f"    - {exp.name} (Status: {exp.status})")
```

### 3. Test GraphQL Query Directly

Test the GraphQL endpoint directly:

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { projects(teamId: \"<your-team-uuid>\") { id name } }"
  }'
```

Then test experiments query:

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { experiments(projectId: \"<your-project-uuid>\") { id name status } }"
  }'
```

### 4. Check Backend Logs

Watch the backend logs when navigating to project detail page:

```bash
# Start backend with logging
alphatrion

# Or with more verbose logging
ALPHATRION_LOG_LEVEL=DEBUG alphatrion
```

Look for:
- GraphQL query being received
- Any errors in processing
- SQL queries being executed

## Common Issues

### Issue 1: No Experiments in Database

**Symptom:** Projects show up, but "0 experiments" or empty list

**Solution:** Run the test data script:

```bash
cd /Users/kerthcet/Workspaces/InftyAI/alphatrion
export ALPHATRION_METADATA_DB_URL='postgresql://user:pass@localhost/db'
python scripts/create_test_data.py
```

### Issue 2: UUID Format Error

**Symptom:** "badly formed hexadecimal UUID string" in backend logs

**Solution:** Check that you're using valid UUIDs:
- Team ID must be a valid UUID
- Project ID must be a valid UUID
- Don't use strings like "default-team"

### Issue 3: GraphQL Query Returns Empty

**Symptom:** Query succeeds but returns empty array

**Check:**
1. Are experiments actually linked to the project?
2. Is the project_id in experiments table set correctly?

```sql
-- Check database directly
SELECT e.id, e.name, e.project_id, p.name as project_name
FROM experiments e
JOIN projects p ON e.project_id = p.id;
```

### Issue 4: CORS or Network Error

**Symptom:** "Failed to fetch" or CORS errors in browser console

**Solution:**
1. Check backend is running on port 8000
2. Verify Vite proxy configuration (for dev mode)
3. Check CORS middleware is configured in backend

## Manual Test

Try this manual test to isolate the issue:

```python
import asyncio
import uuid
import os

os.environ['ALPHATRION_METADATA_DB_URL'] = 'postgresql://user:pass@localhost/db'

import alphatrion
from alphatrion.project import project as proj
from alphatrion.experiment import base as experiment

async def test():
    # Use existing team/user or create new ones
    team_id = uuid.uuid4()
    user_id = uuid.uuid4()

    alphatrion.init(team_id=team_id, user_id=user_id)

    # Create project
    project = proj.Project.setup(name="Debug Test Project")
    print(f"Project ID: {project.id}")

    async with project:
        # Create experiment
        exp = experiment.Experiment.setup(
            name="Debug Test Experiment",
            params={"test": True}
        )

        async with exp:
            alphatrion.log_metrics({"accuracy": 0.95})

        print(f"Experiment ID: {exp.id}")
        print(f"Project ID from exp: {exp._project_id}")

    # Now check in dashboard
    print(f"\nGo to: http://localhost:8000/projects/{project.id}")
    print("You should see 'Debug Test Experiment' in the list")

asyncio.run(test())
```

## Still Having Issues?

If experiments still don't show up, share:

1. **Browser console errors** - Any red errors?
2. **Backend logs** - What does the backend print?
3. **Database check** - Do experiments exist with correct project_id?
4. **GraphQL response** - What does the API return?

### Check GraphQL Response in Browser

1. Open browser DevTools (F12)
2. Go to Network tab
3. Navigate to a project detail page
4. Find the `/graphql` request
5. Check the Response tab

Should see:
```json
{
  "data": {
    "experiments": [
      { "id": "...", "name": "...", "status": "COMPLETED" }
    ]
  }
}
```

If you see `"experiments": []`, the issue is in the backend/database.
If you see errors, check the error message for clues.
