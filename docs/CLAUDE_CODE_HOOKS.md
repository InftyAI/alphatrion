# Claude Code Integration (MLflow-Style)

AlphaTrion integrates with Claude Code using **Stop hooks** - exactly like MLflow does. This captures every conversation automatically with 100% reliability.

## Quick Start (2 Commands)

```bash
# 1. Create user
alphatrion init --username="your-name"

# 2. Generate settings file (use the user_id from step 1)
alphatrion config --user-id="your-user-id" --output=~/.claude/settings.json

# Done! Use Claude normally, everything is tracked automatically
claude
```

## How It Works

Claude Code natively supports hooks that trigger when conversations end. AlphaTrion uses this mechanism to read conversation transcripts and extract metrics. **Each conversation automatically creates a new session.**

```
User finishes conversation in Claude Code
    ↓
Claude Code triggers Stop hook
    ↓
Executes: alphatrion claude-hook stop
    ↓
Passes user_id, team_id, transcript path via stdin
    ↓
AlphaTrion auto-creates session for this conversation
    ↓
Reads transcript (JSONL)
    ↓
Extracts metrics: tokens, duration, model
    ↓
Creates runs in database (direct DB write)
    ↓
Marks session as COMPLETED
    ↓
Done!
```

## Setup (One-Time)

### Step 1: Initialize AlphaTrion

```bash
alphatrion init --username="your-name" --email="your@email.com"
```

**Save the user_id from the output!**

### Step 2: Generate Configuration

**Option A: Print configuration (copy/paste manually)**
```bash
alphatrion config --user-id="your-user-id"
```

**Option B: Write directly to settings file (recommended)**
```bash
alphatrion config --user-id="your-user-id" --output=~/.claude/settings.json
```

This generates:
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "Stop": {
      "command": "alphatrion",
      "args": ["claude-hook", "stop"],
      "stdin": {
        "user_id": "your-user-id",
        "team_id": "your-team-id",
        "agent_name": "claude",
        "transcript_path": "{{ transcript_path }}"
      }
    }
  }
}
```

**Configuration options:**
- `--user-id`: Your user ID (required)
- `--team-id`: Your team ID (optional, auto-detected)
- `--agent-name`: Agent name (default: "claude")
- `--output`: File path to write (default: print to stdout)

### Step 3: Use Claude Code Normally

```bash
claude
```

That's it! Every conversation is automatically tracked:
- **Each conversation** creates a new session
- **Each turn** (user → assistant) creates a new run
- The Stop hook writes directly to the database

### Step 4: View Your Data

When you want to view your tracked conversations:

```bash
# Terminal 1: Start backend server
alphatrion server

# Terminal 2: Launch dashboard
alphatrion dashboard --user-id="your-user-id"
```

Open http://localhost:5173 to see your agents, sessions, runs, and metrics.

## What Gets Captured

**Per Conversation:**
- ✅ **Session** - Auto-created for each conversation
- ✅ **Agent** - Auto-created if doesn't exist (reused across conversations)

**Per Turn (user message → assistant response):**
- ✅ **Run** - One run per interaction within the conversation

✅ **Input/Output**
- User message content
- Assistant response content

✅ **Token Usage**
- Input tokens (including cache)
- Output tokens
- Total tokens

✅ **Timing**
- Response duration (seconds)
- Timestamp

✅ **Model Info**
- Model name (e.g., "claude-3-5-sonnet-20241022")

✅ **Metadata**
- Agent name
- Run name (from user message)

## Architecture

**Simple and Direct:**

```
One-time: Configure ~/.claude/settings.json
          (user_id, team_id, agent_name)

Every conversation: claude
                    ↓
                Stop hook triggers
                    ↓
                Auto-creates session
                    ↓
                Writes runs to database
                    ↓
                Marks session completed

When viewing: alphatrion server + dashboard
              ↓
          Queries database → Shows your data
```

**Key points:**
- Hook writes **directly to database** (no server needed for tracking)
- Server only needed for **dashboard queries**
- **One session per conversation** (automatic)

## Complete Example

```bash
# Step 1: One-time setup
$ alphatrion init --username="Alice" --email="alice@example.com"

✅ Initialization successful!

📋 Your user ID:
   da496d29-2699-4622-937a-239a4dc471a7
   Your team ID:
   777ab400-cc55-46c9-9030-de22d76cd31f

# Step 2: Generate and save configuration (one command!)
$ alphatrion config \
    --user-id="da496d29-2699-4622-937a-239a4dc471a7" \
    --output=~/.claude/settings.json

✅ Configuration saved to: ~/.claude/settings.json

💡 Configuration details:
   User ID:    da496d29-2699-4622-937a-239a4dc471a7
   Team ID:    777ab400-cc55-46c9-9030-de22d76cd31f
   Agent Name: claude

🚀 Now just use Claude normally:
   claude

# Step 3: Use Claude normally - tracking happens automatically!
$ claude
> Hello, can you help me write a Python function?
...
(conversation ends - Stop hook creates session + runs automatically)

$ claude
> How do I fix this bug?
...
(new conversation - new session created automatically)

# Step 4: View your data
$ alphatrion server &
$ alphatrion dashboard --user-id="da496d29-2699-4622-937a-239a4dc471a7"
🌐 Dashboard URL: http://127.0.0.1:5173

# See all your conversations organized by session!
```

## Multiple Agents

To track different agents (e.g., different projects or contexts):

```json
// For work projects
{
  "hooks": {
    "Stop": {
      "stdin": {
        "user_id": "your-user-id",
        "team_id": "your-team-id",
        "agent_name": "work-assistant",
        "transcript_path": "{{ transcript_path }}"
      }
    }
  }
}

// For personal projects
{
  "hooks": {
    "Stop": {
      "stdin": {
        "user_id": "your-user-id",
        "team_id": "your-team-id",
        "agent_name": "personal-assistant",
        "transcript_path": "{{ transcript_path }}"
      }
    }
  }
}
```

Each agent will have its own sessions (one per conversation).

## Transcript Format

Claude Code saves conversations in JSONL format:

```jsonl
{"type":"user","content":"Hello!","timestamp":"2024-03-15T10:00:00Z"}
{"type":"assistant","content":"Hi there!","model":"claude-3-5-sonnet","usage":{"input_tokens":10,"output_tokens":5},"timestamp":"2024-03-15T10:00:02Z"}
{"type":"user","content":"How are you?","timestamp":"2024-03-15T10:00:10Z"}
{"type":"assistant","content":"I'm doing well!","model":"claude-3-5-sonnet","usage":{"input_tokens":15,"output_tokens":8},"timestamp":"2024-03-15T10:00:12Z"}
```

AlphaTrion parses this to:
- Match user→assistant pairs
- Extract tokens from `usage` field
- Calculate duration from timestamps
- Create one run per interaction

## Benefits vs Proxy Approach

| Feature | Stop Hook (This) | Proxy |
|---------|------------------|-------|
| **Reliability** | 100% - Native hook | ~95% - Can fail |
| **SSL Issues** | ❌ None | ✅ Certificate problems |
| **Setup** | One-time config | Install cert + proxy |
| **Performance** | Zero overhead | Slight latency |
| **Works With** | Claude Code only | Any HTTP client |
| **Server** | Only for dashboard | Required for tracking |
| **Session Management** | Auto per conversation | Manual |

## Troubleshooting

### Hook not triggering

1. **Check syntax** in `~/.claude/settings.json`:
   ```bash
   # Validate JSON
   python -m json.tool ~/.claude/settings.json
   ```

2. **Verify alphatrion command**:
   ```bash
   alphatrion claude-hook stop --help
   ```

3. **Check Claude Code version**:
   ```bash
   claude --version
   # Hooks require Claude Code v1.0+
   ```

### No data in dashboard

1. **Verify user/team exist**:
   ```bash
   # Check database
   psql postgresql://alphatrion:alphatr1on@localhost:5432/alphatrion \
     -c "SELECT * FROM users WHERE uuid='YOUR_USER_ID';"
   ```

2. **Check transcript path**:
   - Claude Code saves transcripts to `~/.claude/conversations/`
   - Ensure alphatrion can read this directory

3. **Test hook manually**:
   ```bash
   # Create test transcript
   echo '{"type":"user","content":"test","timestamp":"2026-03-15T22:00:00Z"}
{"type":"assistant","content":"response","model":"claude-3-5-sonnet","usage":{"input_tokens":5,"output_tokens":5},"timestamp":"2026-03-15T22:00:01Z"}' > /tmp/test.jsonl

   # Test hook
   echo '{"user_id":"YOUR_USER_ID","team_id":"YOUR_TEAM_ID","agent_name":"claude","transcript_path":"/tmp/test.jsonl"}' | \
     alphatrion claude-hook stop
   ```

4. **Check database for sessions**:
   ```bash
   psql postgresql://alphatrion:alphatr1on@localhost:5432/alphatrion \
     -c "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;"
   ```

### Permission errors

```bash
# Ensure alphatrion is in PATH
which alphatrion

# If not, use full path in settings.json:
{
  "hooks": {
    "Stop": {
      "command": "/full/path/to/alphatrion",
      ...
    }
  }
}
```

## Comparison with MLflow

This implementation follows MLflow's exact pattern:

```json
// MLflow's approach
{
  "hooks": {
    "Stop": {
      "command": "mlflow",
      "args": ["autolog", "claude", "stop-hook"],
      "stdin": {
        "session_id": "{{ session_id }}",
        "transcript_path": "{{ transcript_path }}"
      }
    }
  }
}

// AlphaTrion's approach (same pattern!)
{
  "hooks": {
    "Stop": {
      "command": "alphatrion",
      "args": ["claude-hook", "stop"],
      "stdin": {
        "session_id": "YOUR_SESSION_ID",
        "transcript_path": "{{ transcript_path }}"
      }
    }
  }
}
```

Both read the same JSONL transcript format and extract the same metrics.

## See Also

- [MLFLOW_AUTOLOG_CLAUDE.md](./MLFLOW_AUTOLOG_CLAUDE.md) - Previous proxy-based approach
- [MLflow Claude Code Blog](https://mlflow.org/blog/mlflow-claude-code) - MLflow's implementation

---

**Simple, reliable Claude Code tracking - the MLflow way!** 🚀
