"""Claude Code hook handler.

Processes Claude Code hooks (SessionStart, Stop, SessionEnd) to automatically track conversations.
Uses Claude's native hook system for reliable, incremental tracking.
"""

import json
import os
import sys
import uuid
from datetime import UTC, datetime

from alphatrion.storage import runtime
from alphatrion.storage.sql_models import Status
from alphatrion.tracing.clickhouse_exporter import determine_semantic_kind


def handle_hook(hook_type: str):
    """Main hook handler that routes to specific hook handlers.

    Args:
        hook_type: Type of hook (session-start, stop, session-end)
    """
    handlers = {
        "session-start": handle_session_start,
        "stop": handle_stop,
        # No need for session-end now.
        # "session-end": handle_session_end,
    }

    handler = handlers.get(hook_type)
    if not handler:
        print(
            json.dumps({"success": False, "error": f"Unknown hook type: {hook_type}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    handler()


def handle_session_start():
    """Handle SessionStart hook - create session with RUNNING status.

    Input from Claude Code:
    {
        "session_id": "abc123",
        "transcript_path": "/path/to/transcript.jsonl",
        "model": "claude-sonnet-4-6",
    }
    """

    try:
        # Read all data from stdin
        stdin_raw = sys.stdin.read()
        input_data = json.loads(stdin_raw)
        session_id = input_data.get("session_id")
        transcript_path = input_data.get("transcript_path")
        model = input_data.get("model", "unknown")
        source = input_data.get("source", "new")

        # Get user_id and team_id from environment variables (required)
        user_id = os.getenv("ALPHATRION_USER_ID")
        team_id = os.getenv("ALPHATRION_TEAM_ID")
        agent_id = os.getenv("ALPHATRION_AGENT_ID")

        if not user_id or not team_id:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "ALPHATRION_USER_ID and ALPHATRION_TEAM_ID environment variables must be set",
                    }
                ),
                file=sys.stderr,
            )
            sys.exit(1)

        print(
            f"DEBUG: SessionStart - session_id={session_id}, source={source}",
            file=sys.stderr,
        )
        print(
            f"DEBUG: SessionStart - user_id={user_id}, team_id={team_id}",
            file=sys.stderr,
        )

        if not session_id or not user_id or not team_id:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "Missing session_id, user_id, or team_id",
                    }
                ),
                file=sys.stderr,
            )
            sys.exit(1)

        # Initialize runtime
        runtime.init()
        metadb = runtime.storage_runtime().metadb

        # Get or create agent
        from pathlib import Path

        from alphatrion.storage.sql_models import AgentType

        agent = metadb.get_agent_by_type(
            user_id=uuid.UUID(user_id),
            agent_type=AgentType.CLAUDE,
        )

        if not agent:
            raise ValueError(
                "Agent not found for user_id. Ensure the agent is created before starting the session."
            )

        # Check if session already exists (for resume/clear/compact)
        session_uuid = uuid.UUID(session_id)
        existing_session = metadb.get_session(session_id=session_uuid)

        if existing_session and source == "resume":
            # Session already exists, just return success
            print(
                json.dumps(
                    {"success": True, "session_id": session_id, "action": "resumed"}
                )
            )
            return

        if existing_session:
            # Session exists but not a resume - just return success
            print(
                f"DEBUG: Session {session_id} already exists (source={source})",
                file=sys.stderr,
            )
            print(
                json.dumps(
                    {"success": True, "session_id": session_id, "action": "existing"}
                )
            )
            return

        # Create new session
        from alphatrion.storage.sql_models import AgentSession

        # Extract project name from transcript path
        project_dir_name = (
            Path(transcript_path).parent.name if transcript_path else None
        )
        project_name = project_dir_name.split("-")[-1] if project_dir_name else None

        db_session = metadb._session()
        session = AgentSession(
            uuid=session_uuid,
            agent_id=agent_id,
            team_id=uuid.UUID(team_id),
            user_id=uuid.UUID(user_id),
            meta={
                "project_name": project_name,
                "model": model,
                "last_processed_timestamp": None,  # Track incremental processing
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(session)
        db_session.commit()
        db_session.close()

        print(f"DEBUG: Created session {session_id}", file=sys.stderr)
        print(
            json.dumps({"success": True, "session_id": session_id, "action": "created"})
        )

    except Exception as e:
        import traceback

        error_msg = f"SessionStart hook failed: {e}\n{traceback.format_exc()}"
        print(json.dumps({"success": False, "error": error_msg}), file=sys.stderr)
        sys.exit(1)


def handle_stop():
    """Handle Stop hook - create runs for new interactions only.

    Input from Claude Code:
    {
        "session_id": "abc123",
        "transcript_path": "/path/to/transcript.jsonl",
        "last_assistant_message": "..."
    }

    Processes only interactions newer than last_processed_timestamp.
    """
    try:
        # Read all data from stdin (including user_id and team_id)
        stdin_raw = sys.stdin.read()
        input_data = json.loads(stdin_raw)
        session_id = input_data.get("session_id")
        transcript_path = input_data.get("transcript_path")

        # Get user_id and team_id from environment variables (required)
        user_id = os.getenv("ALPHATRION_USER_ID")
        team_id = os.getenv("ALPHATRION_TEAM_ID")

        if not user_id or not team_id:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "ALPHATRION_USER_ID and ALPHATRION_TEAM_ID environment variables must be set",
                    }
                ),
                file=sys.stderr,
            )
            sys.exit(1)

        if not session_id or not transcript_path:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "Missing required fields: session_id and transcript_path",
                        "received": {
                            "session_id": session_id,
                            "transcript_path": transcript_path,
                        },
                    }
                ),
                file=sys.stderr,
            )
            sys.exit(1)

        # Initialize runtime
        runtime.init()
        metadb = runtime.storage_runtime().metadb

        # Get session (it should exist from SessionStart hook)
        session_uuid = uuid.UUID(session_id)
        session = metadb.get_session(session_id=session_uuid)

        # If user_id and team_id are null in stdin, get them from the existing session
        if not user_id and session:
            user_id = str(session.user_id)

        if not team_id and session:
            team_id = str(session.team_id)

        if not session:
            # Safety fallback: Create session if SessionStart hook didn't fire
            print(
                f"WARN: Session {session_id} not found, creating it now",
                file=sys.stderr,
            )

            if not user_id or not team_id:
                print(
                    json.dumps(
                        {
                            "success": False,
                            "error": "Session not found and user_id/team_id not provided. Ensure SessionStart hook runs first.",
                            "received": {
                                "session_id": session_id,
                                "user_id": user_id,
                                "team_id": team_id,
                            },
                        }
                    ),
                    file=sys.stderr,
                )
                sys.exit(1)

            from pathlib import Path

            from alphatrion.storage.sql_models import AgentSession, AgentType

            # Get or create agent
            agent = metadb.get_agent_by_type(
                user_id=uuid.UUID(user_id),
                agent_type=AgentType.CLAUDE,
            )

            if not agent:
                agent_id = metadb.create_agent(
                    name="claude",
                    type=AgentType.CLAUDE,
                    team_id=uuid.UUID(team_id),
                    user_id=uuid.UUID(user_id),
                )
            else:
                agent_id = agent.uuid

            # Create session
            project_dir_name = Path(transcript_path).parent.name
            project_name = project_dir_name.split("-")[-1] if project_dir_name else None

            db_session = metadb._session()
            session = AgentSession(
                uuid=session_uuid,
                agent_id=agent_id,
                team_id=uuid.UUID(team_id),
                user_id=uuid.UUID(user_id),
                meta={"project_name": project_name, "last_processed_timestamp": None},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db_session.add(session)
            db_session.commit()
            db_session.close()

        # Process new interactions only
        runs_created = process_transcript_incremental(
            session_id=str(session_uuid),
            transcript_path=transcript_path,
        )

        print(
            json.dumps(
                {
                    "success": True,
                    "session_id": session_id,
                    "runs_created": runs_created,
                }
            )
        )

    except Exception as e:
        import traceback

        error_msg = f"Stop hook failed: {e}\n{traceback.format_exc()}"
        print(json.dumps({"success": False, "error": error_msg}), file=sys.stderr)
        sys.exit(1)


def handle_session_end():
    """Handle SessionEnd hook - cleanup and finalize session.

    Input from Claude Code:
    {
        "session_id": "abc123",
        "user_id": "...",
        "team_id": "..."
    }
    """
    try:
        stdin_raw = sys.stdin.read()

        input_data = json.loads(stdin_raw)
        session_id = input_data.get("session_id")

        if not session_id:
            print(
                json.dumps({"success": False, "error": "Missing session_id"}),
                file=sys.stderr,
            )
            sys.exit(1)

        print(json.dumps({"success": True, "session_id": session_id}))

    except Exception as e:
        import traceback

        error_msg = f"SessionEnd hook failed: {e}\n{traceback.format_exc()}"
        print(json.dumps({"success": False, "error": error_msg}), file=sys.stderr)
        sys.exit(1)


def process_transcript_incremental(
    session_id: str,
    transcript_path: str,
) -> int:
    """Process Claude Code transcript and create runs for NEW interactions only.

    Uses last_processed_timestamp from session metadata to track which interactions
    have already been processed. This allows:
    - Resumed conversations to continue tracking
    - Multiple Stop hooks on same conversation
    - Partial recovery from compacting (if Stop hook fired before compacting)

    WARNING: Data loss possible if:
    - Stop hook fails to execute
    - System crashes before hook runs
    - Compacting removes messages before processing

    Mitigation: Stop hook fires immediately after each response, so data is
    usually processed before compacting. But failures can still cause loss.

    Args:
        session_id: Session UUID to associate runs with
        transcript_path: Path to JSONL transcript file

    Returns:
        Number of new runs created
    """
    # Read transcript file (JSONL format)
    with open(transcript_path) as f:
        transcript_lines = [json.loads(line) for line in f if line.strip()]

    if not transcript_lines:
        return 0

    metadb = runtime.storage_runtime().metadb

    # Get session info
    session = metadb.get_session(session_id=uuid.UUID(session_id))
    if not session:
        raise ValueError(f"Session not found: {session_id}")
    agent = metadb.get_agent(agent_id=session.agent_id)

    # Get last processed timestamp
    last_processed_ts = None
    if session.meta and "last_processed_timestamp" in session.meta:
        last_processed_ts_str = session.meta["last_processed_timestamp"]
        if last_processed_ts_str:
            try:
                last_processed_ts = datetime.fromisoformat(
                    last_processed_ts_str.replace("Z", "+00:00")
                )
                print(
                    f"DEBUG: Last processed timestamp: {last_processed_ts}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(
                    f"WARN: Failed to parse last_processed_timestamp: {e}",
                    file=sys.stderr,
                )
                last_processed_ts = None

    # Safety check: Detect potential data loss from compacting
    # If last_processed_ts exists but earliest message in file is AFTER it,
    # compacting removed messages we never processed
    if transcript_lines and last_processed_ts:
        earliest_msg_ts = None
        for line in transcript_lines[:10]:  # Check first 10 messages
            ts_str = line.get("timestamp")
            if ts_str:
                try:
                    earliest_msg_ts = datetime.fromisoformat(
                        ts_str.replace("Z", "+00:00")
                    )
                    break
                except Exception:
                    continue

        if earliest_msg_ts and earliest_msg_ts > last_processed_ts:
            time_gap = (earliest_msg_ts - last_processed_ts).total_seconds()
            print(
                f"WARNING: Potential data loss detected! "
                f"Last processed: {last_processed_ts}, "
                f"Earliest in file: {earliest_msg_ts}, "
                f"Gap: {time_gap:.1f}s. "
                f"Messages may have been compacted before processing.",
                file=sys.stderr,
            )

    # Find conversation turns (user -> assistant pairs)
    # Only process interactions AFTER last_processed_timestamp
    # Note: One run = user input → all thinking/tool_use → final response (stop_reason="end_turn")
    current_user_msg = None  # The initial user prompt for this turn
    current_assistant_messages = []  # Accumulate ALL assistant messages for current turn
    current_tool_results = []  # Accumulate tool results from tool-result-only user messages
    runs_created = 0
    latest_timestamp = last_processed_ts

    for line in transcript_lines:
        msg_type = line.get("type")
        timestamp_str = line.get("timestamp")

        if not timestamp_str:
            continue

        # Parse timestamp
        try:
            msg_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            print(f"WARN: Invalid timestamp: {timestamp_str}", file=sys.stderr)
            continue

        # Skip if already processed
        if last_processed_ts and msg_timestamp <= last_processed_ts:
            continue

        if msg_type == "user":
            # Check if this is a real user message or just tool results
            user_content = line.get("message", {}).get("content", [])
            is_only_tool_results = False

            if isinstance(user_content, list):
                # Check if message contains ONLY tool_result blocks (no text)
                has_text = any(
                    isinstance(block, dict)
                    and block.get("type") == "text"
                    and block.get("text", "").strip()
                    for block in user_content
                )
                has_tool_results = any(
                    isinstance(block, dict) and block.get("type") == "tool_result"
                    for block in user_content
                )
                is_only_tool_results = has_tool_results and not has_text

            if is_only_tool_results:
                # This is a system-generated tool result message, not a real user message
                # Don't overwrite current_user_msg, but capture tool results for duration calculation

                # Extract tool results with timestamps (make a copy to avoid modifying original)
                for block in user_content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        # Create a copy and attach timestamp
                        block_copy = block.copy()
                        block_copy["_timestamp"] = line.get("timestamp")
                        current_tool_results.append(block_copy)

                continue

            # This is a real user message, store it
            current_user_msg = line

        elif msg_type == "assistant" and current_user_msg:
            # Accumulate ALL assistant messages for this turn
            # (can have multiple message.ids)
            assistant_msg = line
            assistant_message = assistant_msg.get("message", {})

            # Add to current turn
            current_assistant_messages.append(line)

            # Check stop_reason to see if turn is complete
            stop_reason = assistant_message.get("stop_reason")

            if not stop_reason:
                # Turn not complete yet (more messages coming)
                continue

            if stop_reason == "tool_use":
                # Tool execution requested, but turn not complete yet
                # Keep accumulating messages, wait for final response
                continue

            # stop_reason is "end_turn" or other final reason
            # Turn is complete, create run and multiple LLM spans
            user_message = current_user_msg.get("message", {})

            # Calculate total tokens and duration from all messages
            total_input_tokens = 0
            total_output_tokens = 0
            for msg in current_assistant_messages:
                msg_usage = msg.get("message", {}).get("usage", {})
                total_input_tokens += msg_usage.get("input_tokens", 0)
                total_output_tokens += msg_usage.get("output_tokens", 0)
            total_tokens = total_input_tokens + total_output_tokens

            # Calculate duration from timestamps
            # (first user message to last assistant message)
            duration = calculate_duration(
                current_user_msg.get("timestamp"),
                current_assistant_messages[-1].get("timestamp"),
            )

            # Use last message for metadata
            last_message = current_assistant_messages[-1].get("message", {})
            model = last_message.get("model", "unknown")

            # Determine run status from final message
            status_code = "OK"
            status_message = ""
            run_status = Status.COMPLETED

            # Check for error indicators
            if stop_reason == "error" or last_message.get("error"):
                status_code = "ERROR"
                run_status = Status.FAILED
                error_obj = last_message.get("error", {})
                if isinstance(error_obj, dict):
                    error_type = error_obj.get("type", "unknown_error")
                    error_msg = error_obj.get("message", "")
                    status_message = (
                        f"{error_type}: {error_msg}" if error_msg else error_type
                    )
                else:
                    status_message = str(error_obj)
            elif stop_reason == "max_tokens":
                status_code = "OK"
                status_message = "Response truncated: max_tokens reached"

            # Create run with aggregated tokens
            run_id = metadb.create_run(
                session_id=uuid.UUID(session_id),
                team_id=session.team_id,
                user_id=session.user_id,
                status=run_status,
                duration=duration,
                usage={
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "total_tokens": total_tokens,
                },
            )

            # Prepare user content (original user message only)
            # Do NOT include tool_results - they're already stored in tool span outputs
            user_content_blocks = user_message.get("content", "")
            if isinstance(user_content_blocks, str):
                try:
                    user_content_blocks = (
                        json.loads(user_content_blocks) if user_content_blocks else []
                    )
                except Exception:
                    user_content_blocks = (
                        [{"type": "text", "text": user_content_blocks}]
                        if user_content_blocks
                        else []
                    )
            elif not isinstance(user_content_blocks, list):
                user_content_blocks = []

            # Store ONLY the original user input (not tool results)
            # Tool results are already captured in tool span outputs
            user_full_content = (
                json.dumps(user_content_blocks) if user_content_blocks else ""
            )

            # Create one LLM span per assistant message
            create_clickhouse_spans_for_turn(
                run_id=run_id,
                session_id=session_id,
                team_id=str(session.team_id),
                user_id=str(session.user_id),
                user_full_content=user_full_content,
                assistant_messages=current_assistant_messages,
                tool_results=current_tool_results,
                model=model,
                user_timestamp=current_user_msg.get("timestamp"),
                duration=duration,
                status_code=status_code,
                status_message=status_message,
                agent_id=str(agent.uuid),
                agent_type=str(agent.type),
                agent_name=agent.name,
                stop_reason=stop_reason or "",
            )

            runs_created += 1

            # Update latest timestamp (msg_timestamp is already a datetime)
            if not latest_timestamp or msg_timestamp > latest_timestamp:
                latest_timestamp = msg_timestamp

            # Reset for next turn
            current_user_msg = None
            current_assistant_messages = []
            current_tool_results = []

    # Update session metadata with latest processed timestamp
    if latest_timestamp:
        updated_meta = session.meta or {}
        timestamp_str = latest_timestamp.isoformat()
        updated_meta["last_processed_timestamp"] = timestamp_str
        metadb.update_session(session_id=uuid.UUID(session_id), meta=updated_meta)
        print(
            f"DEBUG: Updated last_processed_timestamp to {timestamp_str}",
            file=sys.stderr,
        )

    return runs_created


def calculate_duration(
    user_timestamp: str | None, assistant_timestamp: str | None
) -> float:
    """Calculate duration between user message and assistant response.

    Args:
        user_timestamp: ISO format timestamp of user message
        assistant_timestamp: ISO format timestamp of assistant response

    Returns:
        Duration in seconds, 0.0 if timestamps are invalid
    """
    if not user_timestamp or not assistant_timestamp:
        return 0.0

    try:
        user_time = datetime.fromisoformat(user_timestamp.replace("Z", "+00:00"))
        assistant_time = datetime.fromisoformat(
            assistant_timestamp.replace("Z", "+00:00")
        )
        return (assistant_time - user_time).total_seconds()
    except Exception:
        return 0.0


def build_prompt_attributes(user_full_content: str) -> dict[str, str]:
    """Build Traceloop-style indexed prompt attributes from user content.

    Converts Claude content blocks to gen_ai.prompt.{index}.* attributes.
    Supports text blocks and tool_result blocks.

    Args:
        user_full_content: JSON string of user content blocks

    Returns:
        Dictionary of indexed prompt attributes
    """
    attributes = {}

    try:
        content_blocks = json.loads(user_full_content)
        if not isinstance(content_blocks, list):
            content_blocks = [{"type": "text", "text": str(content_blocks)}]
    except Exception:
        content_blocks = [{"type": "text", "text": user_full_content}]

    # User messages go into gen_ai.prompt.0
    attributes["gen_ai.prompt.0.role"] = "user"

    # Concatenate all text blocks for content
    text_parts = []
    tool_result_counter = 0

    for block in content_blocks:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")

        if block_type == "text":
            text_parts.append(block.get("text", ""))
        elif block_type == "tool_result":
            # Store tool results as separate indexed attributes
            tool_use_id = block.get("tool_use_id", "")
            is_error = block.get("is_error", False)
            content = block.get("content", "")

            attributes[
                f"gen_ai.prompt.0.tool_results.{tool_result_counter}.tool_use_id"
            ] = tool_use_id
            attributes[
                f"gen_ai.prompt.0.tool_results.{tool_result_counter}.is_error"
            ] = str(is_error)
            attributes[
                f"gen_ai.prompt.0.tool_results.{tool_result_counter}.content"
            ] = content if isinstance(content, str) else json.dumps(content)
            tool_result_counter += 1

    attributes["gen_ai.prompt.0.content"] = " ".join(text_parts) if text_parts else ""

    return attributes


def build_completion_attributes(
    assistant_full_content: str,
    tool_executions: dict[str, dict] = None,
    stop_reason: str = "",
) -> dict[str, str]:
    """Build Traceloop-style indexed completion attributes from assistant content.

    Converts Claude content blocks to gen_ai.completion.{index}.* attributes
    including tool_calls with indexed structure. Optionally adds AlphaTrion
    extensions for tool execution details.

    Each tool_use block creates a separate assistant completion block to keep
    tool calls distinct from thinking blocks.

    Args:
        assistant_full_content: JSON string of assistant content blocks
        tool_executions: Optional dict mapping tool_id to execution details
        stop_reason: Stop reason from response

    Returns:
        Dictionary of indexed completion attributes (standard + AlphaTrion extensions)
    """
    attributes = {}

    try:
        content_blocks = json.loads(assistant_full_content)
        if not isinstance(content_blocks, list):
            content_blocks = [{"type": "text", "text": str(content_blocks)}]
    except Exception:
        content_blocks = [{"type": "text", "text": assistant_full_content}]

    completion_idx = 0
    tool_executions = tool_executions or {}

    for block in content_blocks:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")

        # Get timestamp if available (added during message processing)
        block_timestamp = block.get("_timestamp", "")

        if block_type == "text":
            # Text content
            attributes[f"gen_ai.completion.{completion_idx}.role"] = "assistant"
            attributes[f"gen_ai.completion.{completion_idx}.content"] = block.get(
                "text", ""
            )
            if block_timestamp:
                attributes[f"gen_ai.completion.{completion_idx}.timestamp"] = (
                    block_timestamp
                )
            if stop_reason:
                attributes[f"gen_ai.completion.{completion_idx}.finish_reason"] = (
                    stop_reason
                )
            completion_idx += 1

        elif block_type == "thinking":
            # Thinking block (extended thinking)
            attributes[f"gen_ai.completion.{completion_idx}.role"] = "thinking"
            attributes[f"gen_ai.completion.{completion_idx}.content"] = block.get(
                "thinking", ""
            )
            if block_timestamp:
                attributes[f"gen_ai.completion.{completion_idx}.timestamp"] = (
                    block_timestamp
                )
            completion_idx += 1

        elif block_type == "tool_use":
            # Tool call - create a new assistant completion block for this tool
            # This keeps tool calls separate from thinking blocks
            tool_id = block.get("id", "")
            tool_name = block.get("name", "")
            tool_input = block.get("input", {})

            # Standard Traceloop fields
            attributes[f"gen_ai.completion.{completion_idx}.role"] = "assistant"
            attributes[f"gen_ai.completion.{completion_idx}.content"] = ""
            if block_timestamp:
                attributes[f"gen_ai.completion.{completion_idx}.timestamp"] = (
                    block_timestamp
                )

            # Add tool call to this completion block
            # (always index 0 since it's a new block)
            attributes[f"gen_ai.completion.{completion_idx}.tool_calls.0.id"] = tool_id
            attributes[f"gen_ai.completion.{completion_idx}.tool_calls.0.name"] = (
                tool_name
            )
            attributes[f"gen_ai.completion.{completion_idx}.tool_calls.0.arguments"] = (
                json.dumps(tool_input)
            )

            # AlphaTrion extensions (if execution data available)
            if tool_id in tool_executions:
                exec_data = tool_executions[tool_id]
                attributes[
                    f"alphatrion.completion.{completion_idx}.tool_calls.0.timestamp"
                ] = exec_data["timestamp"]
                attributes[
                    f"alphatrion.completion.{completion_idx}.tool_calls.0.duration"
                ] = str(exec_data["duration"])
                attributes[
                    f"alphatrion.completion.{completion_idx}.tool_calls.0.status_code"
                ] = exec_data["status_code"]
                attributes[
                    f"alphatrion.completion.{completion_idx}.tool_calls.0.status_message"
                ] = exec_data["status_message"]
                attributes[
                    f"alphatrion.completion.{completion_idx}.tool_calls.0.output"
                ] = exec_data["output"]

            completion_idx += 1

    # If no content was added, add a default empty completion
    if not attributes:
        attributes["gen_ai.completion.0.role"] = "assistant"
        attributes["gen_ai.completion.0.content"] = ""
        if stop_reason:
            attributes["gen_ai.completion.0.finish_reason"] = stop_reason

    return attributes


def extract_full_content(content) -> str:
    """Extract ALL content including tool use for storage.

    Serializes the full content structure including:
    - text blocks
    - tool_use blocks
    - thinking blocks (if present)

    Args:
        content: Content in various formats

    Returns:
        JSON string of full content structure
    """
    if isinstance(content, str):
        return json.dumps([{"type": "text", "text": content}])
    elif isinstance(content, list):
        # Return full content blocks as JSON
        return json.dumps(content)
    return json.dumps([{"type": "text", "text": str(content)}])


def create_clickhouse_spans_for_turn(
    run_id: uuid.UUID,
    session_id: str,
    team_id: str,
    user_id: str,
    user_full_content: str,
    assistant_messages: list[dict],
    tool_results: list[dict],
    model: str,
    user_timestamp: str,
    duration: float,
    status_code: str = "OK",
    status_message: str = "",
    agent_id: str = "",
    agent_type: str = "",
    agent_name: str = "claude",
    stop_reason: str = "",
) -> None:
    """Create one LLM span per assistant message in ClickHouse.

    Each assistant message line from JSONL becomes one LLM span.
    All spans share the same RunId and TraceId for grouping.

    Args:
        run_id: Run UUID
        session_id: Session UUID
        team_id: Team UUID
        user_id: User UUID
        user_full_content: Full user message structure (JSON) - shared across all spans
        assistant_messages: List of assistant message objects from JSONL
        tool_results: List of tool_result blocks with _timestamp attached
        model: Model name
        user_timestamp: Timestamp of user message
        duration: Duration in seconds for the entire turn
        status_code: Status code (OK, ERROR, UNSET)
        status_message: Human-readable status message (error details)
        agent_id: Agent UUID
        agent_type: Agent type (CLAUDE, CODEX, etc.)
        agent_name: Agent name (for ServiceName)
        stop_reason: Stop reason from Claude response
    """
    try:
        tracestore = runtime.storage_runtime().tracestore
        if not tracestore:
            return

        # Parse timestamp
        base_timestamp = datetime.fromisoformat(user_timestamp.replace("Z", "+00:00"))

        # Generate trace ID (shared across all spans in this turn)
        trace_id = str(uuid.uuid4()).replace("-", "")
        service_name = agent_name

        # Build tool results map with timestamps and content
        tool_results_map = {}
        for b in tool_results:
            tool_use_id = b.get("tool_use_id")
            timestamp_str = b.get("_timestamp")
            if tool_use_id:
                result_data = {
                    "content": b.get("content", ""),
                    "is_error": b.get("is_error", False),
                }
                if timestamp_str:
                    result_data["timestamp"] = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                tool_results_map[tool_use_id] = result_data

        # Build prompt attributes once
        prompt_attributes = build_prompt_attributes(user_full_content)

        # Timeline Construction Strategy:
        # 1. Each assistant message becomes one span with semantic kind
        #    (thinking/tool/text)
        # 2. Start time: message timestamp (when Claude sent it)
        # 3. End time:
        #    - Tool spans: tool result timestamp (actual execution time)
        #    - Other spans: next message timestamp (when next operation starts)
        #    - Last span: small estimate (100ms)
        # 4. Processing spans: auto-inserted to fill gaps > 1ms (like inference time)
        # 5. Tokens: distributed by semantic kind, input tokens only on first span

        # Step 1: Build timeline with actual timestamps
        timeline_items = []  # List of (start_time, end_time, span_dict)

        for idx, msg in enumerate(assistant_messages):
            message_data = msg.get("message", {})
            msg_timestamp_str = msg.get("timestamp")

            # Start time: when this message was generated
            if not msg_timestamp_str:
                continue  # Skip messages without timestamps

            start_time = datetime.fromisoformat(
                msg_timestamp_str.replace("Z", "+00:00")
            )

            # Extract content and tokens
            msg_content = message_data.get("content", [])
            if not isinstance(msg_content, list):
                msg_content = []

            msg_usage = message_data.get("usage", {})
            msg_input_tokens = msg_usage.get("input_tokens", 0)
            msg_output_tokens = msg_usage.get("output_tokens", 0)

            # Determine content type
            tool_use_blocks = [
                b
                for b in msg_content
                if isinstance(b, dict) and b.get("type") == "tool_use"
            ]

            # Calculate end time using actual timestamps only
            end_time = None

            # 1. For tool spans: use tool result timestamp
            if tool_use_blocks:
                tool_use_id = tool_use_blocks[0].get("id")
                result_data = tool_results_map.get(tool_use_id, {})
                end_time = result_data.get("timestamp")

            # 2. For non-tool spans: use next message timestamp
            if not end_time and idx < len(assistant_messages) - 1:
                next_msg_timestamp_str = assistant_messages[idx + 1].get("timestamp")
                if next_msg_timestamp_str:
                    end_time = datetime.fromisoformat(
                        next_msg_timestamp_str.replace("Z", "+00:00")
                    )

            # 3. If no end timestamp: set duration to 0 (no estimation)
            if not end_time:
                end_time = start_time

            # Calculate actual duration
            span_duration = (end_time - start_time).total_seconds()

            # Attach timestamps to content blocks
            for block in msg_content:
                if isinstance(block, dict) and msg_timestamp_str:
                    block["_timestamp"] = msg_timestamp_str

            assistant_full_content = json.dumps(msg_content)

            # Build tool execution map
            tool_executions = {}
            for block in tool_use_blocks:
                tool_id = block.get("id")
                if tool_id:
                    result_data = tool_results_map.get(tool_id, {})
                    result_time = result_data.get("timestamp")
                    is_error = result_data.get("is_error", False)
                    output = result_data.get("content", "")

                    # Calculate duration
                    duration_ns = 0
                    if result_time and msg_timestamp_str:
                        duration_ns = int(
                            (result_time - start_time).total_seconds() * 1_000_000_000
                        )

                    tool_executions[tool_id] = {
                        "timestamp": msg_timestamp_str,
                        "duration": duration_ns,
                        "status_code": "ERROR" if is_error else "OK",
                        "status_message": str(output) if is_error else "",
                        "output": ""
                        if is_error
                        else (
                            output if isinstance(output, str) else json.dumps(output)
                        ),
                    }

            # Generate span ID
            span_id = str(uuid.uuid4()).replace("-", "")[:16]

            # Determine semantic kind
            semantic_kind = determine_semantic_kind({}, msg_content)

            # Token assignment:
            # Each message has actual token usage from Claude API
            # Assign actual tokens to each span for accurate aggregation
            input_tokens = msg_input_tokens
            output_tokens = msg_output_tokens

            # Build span attributes
            span_attributes = {
                "gen_ai.system": "Anthropic",
                "llm.request.type": "chat",
                "gen_ai.request.model": model,
                "gen_ai.response.model": model,
                "gen_ai.usage.input_tokens": str(input_tokens),
                "gen_ai.usage.output_tokens": str(output_tokens),
                "llm.usage.total_tokens": str(input_tokens + output_tokens),
            }

            # Add prompt to first span only (where the user input is sent)
            if idx == 0:
                span_attributes.update(prompt_attributes)

            # Add completion attributes
            span_attributes.update(
                build_completion_attributes(
                    assistant_full_content, tool_executions, stop_reason
                )
            )

            # Create span dict
            span = {
                "Timestamp": start_time,
                "TraceId": trace_id,
                "SpanId": span_id,
                "ParentSpanId": "",
                "SpanName": "anthropic.chat",
                "SpanKind": "CLIENT",
                "SemanticKind": semantic_kind,
                "ServiceName": service_name,
                "Duration": int(span_duration * 1_000_000_000),
                "StatusCode": status_code
                if idx == len(assistant_messages) - 1
                else "OK",
                "StatusMessage": status_message
                if idx == len(assistant_messages) - 1
                else "",
                "TeamId": team_id,
                "UserId": user_id,
                "RunId": str(run_id),
                "SessionId": session_id,
                "AgentId": agent_id,
                "AgentType": agent_type,
                "ExperimentId": "",
                "SpanAttributes": span_attributes,
                "ResourceAttributes": {
                    "service.name": service_name,
                    "agent.id": agent_id,
                    "agent.type": agent_type,
                    "agent.name": agent_name,
                },
                "Events.Timestamp": [],
                "Events.Name": [],
                "Events.Attributes": [],
                "Links.TraceId": [],
                "Links.SpanId": [],
                "Links.Attributes": [],
            }

            timeline_items.append((start_time, end_time, span))

        # Step 2: Sort timeline by start time
        timeline_items.sort(key=lambda x: x[0])

        # Step 3: Detect gaps and insert processing spans
        final_spans = []
        prev_end = base_timestamp

        for start_time, end_time, span in timeline_items:
            # Check for gap
            gap = (start_time - prev_end).total_seconds()
            if gap > 0:  # > 0ms
                processing_span = {
                    "Timestamp": prev_end,
                    "TraceId": trace_id,
                    "SpanId": str(uuid.uuid4()).replace("-", "")[:16],
                    "ParentSpanId": "",
                    "SpanName": "processing",
                    "SpanKind": "INTERNAL",
                    "SemanticKind": "processing",
                    "ServiceName": service_name,
                    "Duration": int(gap * 1_000_000_000),
                    "StatusCode": "OK",
                    "StatusMessage": "",
                    "TeamId": team_id,
                    "UserId": user_id,
                    "RunId": str(run_id),
                    "SessionId": session_id,
                    "AgentId": agent_id,
                    "AgentType": agent_type,
                    "ExperimentId": "",
                    "SpanAttributes": {},
                    "ResourceAttributes": {
                        "service.name": service_name,
                        "agent.id": agent_id,
                        "agent.type": agent_type,
                        "agent.name": agent_name,
                    },
                    "Events.Timestamp": [],
                    "Events.Name": [],
                    "Events.Attributes": [],
                    "Links.TraceId": [],
                    "Links.SpanId": [],
                    "Links.Attributes": [],
                }
                final_spans.append(processing_span)

            # Add operation span
            final_spans.append(span)
            prev_end = end_time

        # Insert all spans
        if final_spans:
            import logging

            processing_count = sum(
                1 for s in final_spans if s.get("SemanticKind") == "processing"
            )
            operation_count = len(final_spans) - processing_count
            logging.debug(
                f"Run {run_id}: {operation_count} operations + {processing_count} \
                    processing gaps = {len(final_spans)} total spans"
            )
            tracestore.insert_spans(final_spans)

    except Exception as e:
        import logging

        logging.error(f"Failed to create ClickHouse spans: {e}", exc_info=True)
