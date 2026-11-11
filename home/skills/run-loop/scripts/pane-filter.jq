# Render codex exec --json events in an optional read-only tmux pane.
if .type == "thread.started" then
  "[start] thread=\(.thread_id)"
elif .type == "item.completed" and .item.type == "agent_message" then
  .item.text
elif .type == "item.started" and .item.type == "command_execution" then
  "[command] \(.item.command | .[0:160])"
elif .type == "item.completed" and .item.type == "command_execution" then
  "[exit] \(.item.exit_code)"
elif .type == "item.completed" and .item.type == "file_change" then
  "[files] \(.item.status)"
elif .type == "turn.completed" then
  "[done]"
elif .type == "turn.failed" then
  "[failed] \(.error.message // .message // "unknown")"
elif .type == "error" then
  "[error] \(.message // .error.message // "unknown")"
else empty end
