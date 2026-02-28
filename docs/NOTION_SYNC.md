# Notion Sync Documentation

## Overview

KIVA-CLI provides bidirectional synchronization between GitHub issues/PRs and Notion databases, enabling seamless workflow integration across both platforms.

**Key Features**:
- ✅ Real-time sync GitHub ↔ Notion
- ✅ Automatic conflict resolution (4 strategies)
- ✅ IntentHash¹¹ tracking for all operations
- ✅ Base-3 ternary validation (PENDING/SUCCESS/FAILED)
- ✅ Batch operations for bulk sync
- ✅ Background daemon for continuous monitoring
- ✅ GitHub Actions workflow for CI/CD integration
- ✅ φ-CPS delta tracking

## Quick Start

### 1. Setup Credentials

```bash
# Set environment variables
export KIVA_GITHUB_REPO="owner/repo"
export KIVA_NOTION_DB_ID="your-notion-database-id"
export NOTION_TOKEN="your-notion-integration-token"
export GITHUB_TOKEN="your-github-token"
```

### 2. Create Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "+ New integration"
3. Name it "KIVA-CLI Sync"
4. Copy the Internal Integration Token
5. Share your database with the integration

### 3. Get Notion Database ID

```bash
# From Notion database URL:
# https://notion.so/workspace/DatabaseName-{DATABASE_ID}?v=...
# Extract the DATABASE_ID part (32 characters)
```

### 4. Run Manual Sync

```python
from kiva_cli.managers.notion_sync_manager import (
    NotionSyncManager,
    SyncConfig
)

# Configure sync
config = SyncConfig(
    github_repo="owner/repo",
    notion_database_id="your-db-id",
    sync_interval_seconds=300,
    bidirectional=True,
    conflict_strategy="notion_wins"
)

# Initialize manager
manager = NotionSyncManager(config)

# Sync GitHub issue to Notion
issue_data = {
    "number": 42,
    "title": "Feature request",
    "state": "open",
    "labels": [{"name": "enhancement"}],
    "assignees": [{"login": "username"}],
    "html_url": "https://github.com/owner/repo/issues/42",
    "created_at": "2026-02-28T10:00:00Z",
    "updated_at": "2026-02-28T12:00:00Z"
}

event = manager.sync_github_issue_to_notion(issue_data)
print(f"Sync status: {event.status}")
print(f"Δφ-CPS: +{event.delta_phi}")
```

## Daemon Mode

### Start Daemon

```bash
# Start background sync daemon
python -m kiva_cli.daemons.notion_sync_daemon start \
  --github-repo owner/repo \
  --notion-db-id your-db-id \
  --interval 300 \
  --conflict-strategy notion_wins
```

### Daemon Management

```bash
# Check daemon status
python -m kiva_cli.daemons.notion_sync_daemon status

# Stop daemon
python -m kiva_cli.daemons.notion_sync_daemon stop

# Restart daemon
python -m kiva_cli.daemons.notion_sync_daemon restart
```

### Daemon Logs

```bash
# View logs
tail -f ~/.kiva/logs/notion_sync.log

# View sync history
ls ~/.kiva/sync_history/
cat ~/.kiva/sync_history/history_20260228_180000.json
```

## GitHub Actions Integration

### Setup Secrets

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets:
   - `NOTION_TOKEN`: Your Notion integration token
   - `NOTION_DATABASE_ID`: Your Notion database ID

### Workflow Configuration

The workflow `.github/workflows/notion_sync.yml` is automatically triggered on:

- **Issue events**: opened, edited, closed, reopened, labeled, unlabeled, assigned, unassigned
- **PR events**: opened, edited, closed, reopened, labeled, unlabeled
- **Schedule**: Every 5 minutes (cron)
- **Manual dispatch**: On-demand via GitHub UI

### Manual Workflow Trigger

1. Go to GitHub repo → Actions → "Notion Sync Automation"
2. Click "Run workflow"
3. Select sync direction:
   - `bidirectional`: Both GitHub → Notion and Notion → GitHub
   - `github_to_notion`: Only GitHub → Notion
   - `notion_to_github`: Only Notion → GitHub
4. Optionally enable "Force full sync"
5. Click "Run workflow"

## Conflict Resolution Strategies

### 1. `notion_wins` (Default)

Notion data takes precedence over GitHub.

**Use when**:
- Notion is the primary workspace
- Team collaborates mainly in Notion
- GitHub is updated automatically

```python
config = SyncConfig(
    github_repo="owner/repo",
    notion_database_id="db-id",
    conflict_strategy="notion_wins"
)
```

### 2. `github_wins`

GitHub data takes precedence over Notion.

**Use when**:
- GitHub is the source of truth
- Developers work primarily in GitHub
- Notion is for visibility only

```python
config = SyncConfig(
    github_repo="owner/repo",
    notion_database_id="db-id",
    conflict_strategy="github_wins"
)
```

### 3. `merge`

Intelligent merge of both sources.

**Strategy**:
- Use most recent timestamp for text fields
- Union merge for labels and assignees
- Prefer Notion for descriptive content
- Prefer GitHub for metadata

**Use when**:
- Both platforms are actively used
- Need best of both worlds
- Want to preserve all data

```python
config = SyncConfig(
    github_repo="owner/repo",
    notion_database_id="db-id",
    conflict_strategy="merge"
)
```

### 4. `manual`

Log conflicts for human review without auto-resolution.

**Use when**:
- Critical data that needs manual review
- Testing sync configuration
- Compliance requirements

```python
config = SyncConfig(
    github_repo="owner/repo",
    notion_database_id="db-id",
    conflict_strategy="manual"
)
```

## Notion Database Schema

### Required Properties

Your Notion database must have these properties:

| Property Name | Type | Description |
|---------------|------|-------------|
| **Issue Number** | Number | GitHub issue/PR number |
| **Title** | Title | Issue/PR title |
| **Status** | Select | "Open" or "Closed" |
| **Labels** | Multi-select | GitHub labels |
| **Assignees** | Multi-select | GitHub usernames |
| **GitHub URL** | URL | Link to GitHub issue/PR |
| **Created** | Date | Creation timestamp |
| **Updated** | Date | Last update timestamp |
| **Source** | Select | "GitHub" (auto-populated) |
| **Last Sync** | Date | Last sync timestamp |

### Create Database Template

```bash
# Use KIVA-CLI to create pre-configured database
kiva notion create-db \
  --name "GitHub Issues Tracker" \
  --template github-issues
```

## Batch Operations

### Sync All Issues

```python
from github import Github

# Fetch all open issues
g = Github("your-github-token")
repo = g.get_repo("owner/repo")
issues = repo.get_issues(state="open")

# Convert to dict format
issue_data_list = [
    {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "labels": [{"name": label.name} for label in issue.labels],
        "assignees": [{"login": assignee.login} for assignee in issue.assignees],
        "html_url": issue.html_url,
        "created_at": issue.created_at.isoformat(),
        "updated_at": issue.updated_at.isoformat()
    }
    for issue in issues
]

# Batch sync
events = manager.sync_all_github_issues(issue_data_list)
print(f"Synced {len(events)} issues")
```

### Sync Recent Notion Updates

```python
from notion_client import Client
from datetime import datetime, timedelta

# Initialize Notion client
notion = Client(auth="your-notion-token")

# Query pages edited in last hour
one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
results = notion.databases.query(
    database_id="your-db-id",
    filter={
        "timestamp": "last_edited_time",
        "last_edited_time": {
            "after": one_hour_ago
        }
    }
)

# Batch sync to GitHub
events = manager.sync_all_notion_pages(results["results"])
print(f"Synced {len(events)} pages")
```

## IntentHash¹¹ Tracking

All sync operations generate IntentHash values for traceability.

### View Sync Event Hash

```python
event = manager.sync_github_issue_to_notion(issue_data)

print(f"Pre-sync hash:  {event.intent_hash_pre}")
print(f"Post-sync hash: {event.intent_hash_post}")
print(f"Event ID:       {event.event_id}")
```

### Export Hash Chain

```python
from pathlib import Path

# Export sync history with hashes
history_file = Path("sync_history.json")
manager.export_sync_history(history_file)

# Parse and verify chain
import json
with open(history_file) as f:
    history = json.load(f)

for event in history:
    print(f"{event['event_id']}: {event['intent_hash_pre']} → {event['intent_hash_post']}")
```

## Base-3 Validation

Sync operations use ternary logic:

- **PENDING**: Operation in progress
- **SUCCESS**: Operation completed successfully
- **FAILED**: Operation failed with error

```python
event = manager.sync_github_issue_to_notion(issue_data)

if event.status == "SUCCESS":
    print("✅ Sync successful")
    print(f"Δφ-CPS: +{event.delta_phi}")
elif event.status == "FAILED":
    print("❌ Sync failed")
    print(f"Error: {event.error}")
else:
    print("⏳ Sync pending")
```

## Monitoring & Metrics

### Get Sync Statistics

```python
stats = manager.get_sync_stats()

print(f"Total events:    {stats['total_events']}")
print(f"Successful:      {stats['successful']}")
print(f"Failed:          {stats['failed']}")
print(f"Pending:         {stats['pending']}")
print(f"Success rate:    {stats['success_rate']:.2%}")
print(f"Total Δφ-CPS:    +{stats['total_delta_phi']:.4f}")
print(f"Last sync:       {stats['last_sync_time']}")
```

### View Sync History

```python
for event in manager.sync_history:
    print(f"{event.timestamp.isoformat()} - "
          f"{event.source} → {event.target} - "
          f"{event.entity_type} #{event.entity_id} - "
          f"{event.status}")
```

## Error Handling

### Handle Failed Syncs

```python
event = manager.sync_github_issue_to_notion(issue_data)

if event.status == "FAILED":
    # Log error
    logger.error(f"Sync failed: {event.error}")
    
    # Retry with exponential backoff
    import time
    max_retries = 3
    for attempt in range(max_retries):
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
        retry_event = manager.sync_github_issue_to_notion(issue_data)
        if retry_event.status == "SUCCESS":
            print("✅ Retry successful")
            break
```

### Daemon Auto-Recovery

The daemon automatically handles:
- Network failures (retry with backoff)
- API rate limits (wait and retry)
- Transient errors (automatic retry)
- Crashes (PID file cleanup)

## Advanced Usage

### Custom Sync Logic

```python
class CustomNotionSyncManager(NotionSyncManager):
    """Extended sync manager with custom logic"""
    
    def sync_github_issue_to_notion(self, issue_data):
        # Pre-processing
        if "security" in [label["name"] for label in issue_data.get("labels", [])]:
            # Skip security-sensitive issues
            return self._create_skipped_event("Security issue skipped")
        
        # Call parent method
        return super().sync_github_issue_to_notion(issue_data)
```

### Webhooks Integration

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook/github", methods=["POST"])
def github_webhook():
    """Handle GitHub webhook events"""
    event = request.headers.get("X-GitHub-Event")
    payload = request.json
    
    if event == "issues":
        manager.sync_github_issue_to_notion(payload["issue"])
    
    return {"status": "ok"}

app.run(port=8080)
```

## Troubleshooting

### Sync Not Working

**Check credentials**:
```bash
echo $NOTION_TOKEN
echo $KIVA_NOTION_DB_ID
echo $GITHUB_TOKEN
```

**Verify Notion integration has access**:
1. Open Notion database
2. Click "⋯" (top right) → Connections
3. Ensure your integration is listed

**Check daemon status**:
```bash
python -m kiva_cli.daemons.notion_sync_daemon status
```

### Rate Limiting

**GitHub**: 5,000 requests/hour (authenticated)
**Notion**: 3 requests/second

**Solution**: Increase sync interval
```python
config = SyncConfig(
    github_repo="owner/repo",
    notion_database_id="db-id",
    sync_interval_seconds=600  # 10 minutes instead of 5
)
```

### Conflict Loops

If syncs keep overwriting each other:

1. Set `conflict_strategy="merge"`
2. Add "Last Modified By" field to track origin
3. Implement conflict detection logic

## Performance Optimization

### Batch Processing

```python
# Instead of syncing one by one
for issue in issues:
    manager.sync_github_issue_to_notion(issue)  # ❌ Slow

# Use batch operation
manager.sync_all_github_issues(issues)  # ✅ Fast
```

### Incremental Sync

```python
# Only sync issues modified since last sync
last_sync = manager.last_sync_time

if last_sync:
    issues = repo.get_issues(
        state="all",
        since=last_sync
    )
else:
    issues = repo.get_issues(state="all")
```

## Integration with ECOYSTEM

NotionSync integrates with Global WAL Manager:

```python
from kiva_cli.core.global_wal_manager import GlobalWALManager

# Log sync events to WAL
wal = GlobalWALManager()
for event in manager.sync_history:
    wal.append_event(
        event_type="notion_sync",
        entity_id=event.entity_id,
        intent_hash=event.intent_hash_post,
        delta_phi=event.delta_phi
    )
```

## References

- [Notion API Documentation](https://developers.notion.com/)
- [GitHub REST API](https://docs.github.com/en/rest)
- [KIVA-CLI GitHub](https://github.com/gerivdb/KIVA-CLI)
- [IntentHash Specification](https://github.com/gerivdb/ECOYSTEM/blob/main/docs/INTENTHASH.md)
- [Base-3 Validation Guide](https://github.com/gerivdb/ECOYSTEM/blob/main/docs/BASE3.md)

## Generated by KIVA-CLI

Date: 2026-02-28  
Version: 1.1.0  
IntentHash: 0x3E9D7A4C8B2F1E5A
