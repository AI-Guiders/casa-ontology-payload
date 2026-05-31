# Shared KB path for experiment scripts (optional sibling repo).
# Set before running:  $env:AGENT_NOTES_KB = '/path/to/agent-notes/knowledge'
function Require-AgentNotesKb {
    if (-not $env:AGENT_NOTES_KB) {
        throw @'
AGENT_NOTES_KB is not set. Point it at your agent-notes/knowledge checkout, e.g.:
  $env:AGENT_NOTES_KB = (Join-Path (Split-Path $PWD -Parent) 'agent-notes/knowledge')
'@
    }
}
