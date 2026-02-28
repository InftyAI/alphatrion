# AlphaTrion Dashboard Setup Guide

## Issue Fixed: UUID Format Error

The "badly formed hexadecimal UUID string" error occurs when the backend expects UUID format for all IDs, but no teams exist in the database yet.

**Solution**: The dashboard now automatically fetches teams and shows a helpful message if none exist.

## Quick Start

### 1. Create Test Data

First, create a team, user, and experiments for testing:

```bash
cd /Users/kerthcet/Workspaces/InftyAI/alphatrion

# Make sure your database is configured
export ALPHATRION_METADATA_DB_URL='postgresql://user:password@localhost/alphatrion'

# Optional: Initialize database tables on first run
export ALPHATRION_INIT_METADATA_TABLES='true'

# Run the test data script
python scripts/create_test_data.py
```

This will create:
- ✅ A test team with UUID
- ✅ A test user with UUID
- ✅ 3 sample experiments with different configurations and labels
- ✅ Sample metrics for each experiment

### 2. Start the Backend

```bash
cd /Users/kerthcet/Workspaces/InftyAI/alphatrion
alphatrion

# Or with uvicorn directly:
# uvicorn alphatrion.server.cmd.app:app --reload
```

The backend will start on **http://localhost:8000**

### 3. View the Dashboard

**Option A: Production Mode (served by backend)**
```bash
# Build the dashboard first
cd dashboard
npm run build

# Then access via backend
# Open http://localhost:8000
```

**Option B: Development Mode (with hot-reload)**
```bash
cd dashboard
npm run dev

# Open http://localhost:5173
```

## Dashboard Features

The dashboard follows a clean hierarchical structure: **Experiments → Runs → Metrics**

### Navigation Structure

**Sidebar Menu:**
- 🏠 **Dashboard** - Overview with quick stats and recent experiments
- 🧪 **Experiments** - Browse all experiments
  - Filter experiments by labels
  - Click an experiment → View runs and metrics
- 📦 **Artifacts** - Browse ORAS registry artifacts
- 🔗 **Tracing** - View roadmap for future tracing features

### Key Features

1. **Dashboard Overview**
   - Quick stats showing teams and experiments count
   - Visual hierarchy explanation
   - Recent experiments list
   - Getting started guide

2. **Experiments Page**
   - List all experiments in your team
   - Filter by labels for organization
   - Click any experiment to view details

3. **Experiment Detail Page**
   - View experiment parameters, metadata, and labels
   - See experiment status, duration, and parameters
   - Click to view run details

4. **Run Detail Page**
   - View run metadata
   - Real-time metrics charts with auto-refresh
   - View all metrics for the run
   - Compare with other runs

5. **Experiment Comparison**
   - Side-by-side parameter diff
   - Metrics overlay chart
   - Highlight differences between experiments

6. **Artifacts Browser**
   - Browse ORAS registry
   - View manifests and layers
   - Download artifacts

## Troubleshooting

### Still getting UUID errors?

**Check if teams exist:**
```python
import os
os.environ['ALPHATRION_METADATA_DB_URL'] = 'your_db_url'

from alphatrion.storage.sqlstore import SQLStore
db = SQLStore(os.environ['ALPHATRION_METADATA_DB_URL'])
teams = db.list_teams()
print(f"Found {len(teams)} teams")
for team in teams:
    print(f"  Team: {team.name} (ID: {team.uuid})")
```

**If no teams exist:**
Run the `create_test_data.py` script above, or create one manually:

```python
import uuid
import alphatrion

team_id = uuid.uuid4()
user_id = uuid.uuid4()

alphatrion.init(team_id=team_id, user_id=user_id)
# Now create experiments...
```

### Dashboard shows "No teams found"

This means no teams exist in your database yet. Run the test data script to create one.

### GraphQL errors in browser console

1. Check that the backend is running on the correct port (default: 8000)
2. Verify the proxy configuration in `dashboard/vite.config.ts` matches your backend port
3. Check browser console for specific error messages

### Artifacts not loading

1. Ensure `ALPHATRION_ARTIFACT_REGISTRY_URL` is set
2. Check that ORAS registry is accessible
3. Verify artifacts exist in the registry

## Environment Variables

Required:
```bash
ALPHATRION_METADATA_DB_URL='postgresql://user:pass@localhost/dbname'
```

Optional:
```bash
ALPHATRION_INIT_METADATA_TABLES='true'  # Initialize tables on first run
ALPHATRION_ARTIFACT_REGISTRY_URL='your-oras-registry-url'
ALPHATRION_ARTIFACT_INSECURE='false'
ALPHATRION_ENABLE_ARTIFACT_STORAGE='true'
ALPHATRION_ENABLE_TRACING='true'
```

## Next Steps

1. **Create real experiments** - Use the AlphaTrion SDK in your ML code
2. **Test polling** - Create a long-running experiment and watch real-time updates
3. **Compare experiments** - Select multiple experiments and compare parameters
4. **Explore artifacts** - Upload and browse experiment artifacts via ORAS

## Support

For issues or questions:
- Check the main README.md
- Open an issue at: https://github.com/InftyAI/alphatrion/issues
