# Metrics Dashboard Guide

**Version**: 1.0.0  
**Last Updated**: 2026-02-28  
**Ecosystem**: ecosystem-1  
**Mode**: H0 Autonomous

---

## Table of Contents

1. [Overview](#overview)
2. [Dashboard Types](#dashboard-types)
3. [Data Sources](#data-sources)
4. [Generating Dashboards](#generating-dashboards)
5. [Dashboard Sections](#dashboard-sections)
6. [Metrics Reference](#metrics-reference)
7. [Visualization](#visualization)
8. [Export Formats](#export-formats)
9. [Automation](#automation)
10. [Customization](#customization)

---

## Overview

The Metrics Dashboard provides real-time insights into the ecosystem-1 health, activity, and φ-CPS evolution across 11 repositories.

### Key Features

- **Real-Time Metrics**: Git statistics, commits, issues, PRs
- **φ-CPS Tracking**: Drift monitoring and trend analysis
- **Repository Status**: Health checks and capability tracking
- **Event Timeline**: Recent activity across ecosystem
- **Comparative Analysis**: Repo-to-repo benchmarks
- **Export Options**: Markdown, JSON, HTML formats
- **Automated Generation**: GitHub Actions integration

### Use Cases

- 📊 **Project Management**: Track progress across repos
- 🔍 **Health Monitoring**: Identify inactive or drifting repos
- 📈 **Trend Analysis**: Visualize φ-CPS evolution over time
- 🚨 **Alert System**: Detect anomalies and drift
- 📑 **Reporting**: Generate stakeholder reports
- 🔧 **Optimization**: Identify bottlenecks and inefficiencies

---

## Dashboard Types

### 1. Ecosystem Overview Dashboard

**Purpose**: High-level ecosystem health and status  
**Frequency**: Daily (automated)  
**Output**: `metrics_dashboard.md`

**Sections**:
- Ecosystem summary
- Repository status matrix
- Global metrics
- φ-CPS analysis
- Recent events (last 10)
- Top active repositories

### 2. Repository Deep-Dive Dashboard

**Purpose**: Detailed analysis of single repository  
**Frequency**: On-demand  
**Output**: `repo_{name}_metrics.md`

**Sections**:
- Repository overview
- Commit history (30 days)
- Contributor activity
- Issue/PR statistics
- Code churn analysis
- Capability assessment

### 3. φ-CPS Drift Dashboard

**Purpose**: φ-CPS tracking and validation  
**Frequency**: Continuous (on sync)  
**Output**: `phi_cps_drift_report.md`

**Sections**:
- φ-CPS baseline vs current
- Phase-by-phase drift breakdown
- Cumulative drift analysis
- Threshold breach alerts
- IntentHash¹¹ chain validation

### 4. Comparative Analysis Dashboard

**Purpose**: Benchmark repositories against each other  
**Frequency**: Weekly  
**Output**: `comparative_metrics.md`

**Sections**:
- Side-by-side repo comparison
- Activity ranking
- Capability matrix
- φ-CPS distribution
- Performance benchmarks

---

## Data Sources

### Primary Sources

1. **ECOS_ROOT.json**: Ecosystem manifest
   - Repository metadata
   - Global metrics
   - Recent events
   - Capabilities

2. **global_wal.db**: Write-Ahead Log
   - Event history
   - IntentHash¹¹ chain
   - φ-CPS deltas
   - Operation logs

3. **Git Repositories**: Live data
   - Commit counts
   - Branch information
   - Contributor stats
   - File metrics

4. **GitHub API**: Real-time data
   - Issues and PRs
   - Contributors
   - Releases
   - Actions status

### Data Collection

```python
# Example data collection
from scripts.ecosystem_metrics_dashboard import EcosystemMetrics

metrics = EcosystemMetrics(root_dir=Path(".."))

# Collect all data
data = metrics.collect_data()
# {
#   "repositories": { /* per-repo stats */ },
#   "global": { /* ecosystem aggregates */ },
#   "phi_cps": { /* drift analysis */ },
#   "events": [ /* recent events */ ]
# }
```

---

## Generating Dashboards

### Quick Start

```bash
# Generate ecosystem overview
python scripts/ecosystem_metrics_dashboard.py \
  --root .. \
  --format markdown \
  --output metrics_dashboard.md
```

### Command-Line Interface

**Script**: `scripts/ecosystem_metrics_dashboard.py`

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--root` | str | `..` | Root directory containing repos |
| `--format` | str | `markdown` | Output format: markdown, json, html |
| `--output` | str | `metrics_dashboard.md` | Output file path |
| `--dashboard` | str | `overview` | Dashboard type: overview, repo, drift, compare |
| `--repo-name` | str | None | Repository name (for repo dashboard) |
| `--days` | int | 30 | Days to include in analysis |
| `--include-charts` | flag | False | Generate charts (requires matplotlib) |

**Examples**:

```bash
# Ecosystem overview (Markdown)
python scripts/ecosystem_metrics_dashboard.py \
  --root ~/projects \
  --format markdown

# JSON export
python scripts/ecosystem_metrics_dashboard.py \
  --format json \
  --output metrics.json

# Repository deep-dive
python scripts/ecosystem_metrics_dashboard.py \
  --dashboard repo \
  --repo-name KIVA-CLI

# φ-CPS drift report
python scripts/ecosystem_metrics_dashboard.py \
  --dashboard drift \
  --output phi_drift.md

# Comparative analysis
python scripts/ecosystem_metrics_dashboard.py \
  --dashboard compare \
  --output comparison.md

# HTML with charts
python scripts/ecosystem_metrics_dashboard.py \
  --format html \
  --include-charts \
  --output dashboard.html
```

---

## Dashboard Sections

### Ecosystem Summary

**Content**:
- Total repositories
- Active vs inactive count
- Total commits (all time + last 30 days)
- Open issues and PRs
- Average φ-CPS
- Top contributors

**Example Output**:
```markdown
## Ecosystem Summary

| Metric | Value |
|--------|-------|
| Total Repositories | 11 |
| Active Repositories | 11 |
| Total Commits | 20 |
| Open Issues | 0 |
| Closed Issues | 4 |
| Average φ-CPS | 4.106 |
| φ-CPS Drift | +0.134 (+3.27%) |
```

### Repository Status Matrix

**Content**:
- Repository name and role
- Status (ACTIVE/INACTIVE/DEPRECATED)
- φ-CPS value
- Commit count
- Open issues
- Last activity date

**Example Output**:
```markdown
## Repository Status

| Repository | Role | Status | φ-CPS | Commits | Issues | Last Activity |
|------------|------|--------|-------|---------|--------|---------------|
| KIVA-CLI | orchestrator | ACTIVE | 4.226 | 19 | 0 | 2026-02-28 |
| ECOYSTEM | core | ACTIVE | 4.094 | 1 | 0 | 2026-02-28 |
| DevTools | utility | ACTIVE | 4.092 | 0 | 0 | N/A |
```

### φ-CPS Analysis

**Content**:
- φ-CPS genesis baseline
- Current φ-CPS value
- Total drift (absolute + percentage)
- Phase-by-phase breakdown
- Drift status (acceptable/warning/critical)

**Example Output**:
```markdown
## φ-CPS Analysis

### Overview
- **φ_genesis**: 4.092
- **φ_current**: 4.226
- **Δφ_total**: +0.134 (+3.27%)
- **Status**: ✅ ACCEPTABLE (< 5% threshold)

### Phase Breakdown
| Phase | Δφ | Percentage |
|-------|-----|------------|
| 1A | +0.035 | 26.1% |
| 1B | +0.044 | 32.8% |
| 1D | +0.031 | 23.1% |
| 2A | +0.018 | 13.4% |
| 2B | +0.006 | 4.5% |
```

### Recent Events

**Content**:
- Last 10 events from ECOS_ROOT.json
- Event type, repo, description
- Timestamp and φ-CPS delta
- IntentHash reference

**Example Output**:
```markdown
## Recent Events

1. **ECOYSTEM sync** (2026-02-28)
   - Synced ECOS_ROOT.json from KIVA-CLI
   - Δφ: +0.002
   - IntentHash: 0x8E4D2A9F7C5B1E3A-SYNC-ROOT

2. **GitHub Actions** (2026-02-28)
   - Deployed ecosystem_sync.yml workflow
   - Δφ: +0.003
   - IntentHash: 0x9C7E4D2A8F5B1E3A-ACTIONS-SYNC
```

### Top Active Repositories

**Content**:
- Ranking by commit count (last 30 days)
- Activity score
- Key contributions

**Example Output**:
```markdown
## Top Active Repositories (Last 30 Days)

1. **KIVA-CLI** - 19 commits
   - Cross-repo sync automation
   - GitHub Actions CI/CD
   - Documentation updates

2. **ECOYSTEM** - 1 commit
   - ECOS_ROOT.json sync

3. **DevTools** - 0 commits
   - Pending first sync
```

---

## Metrics Reference

### Repository Metrics

| Metric | Description | Source |
|--------|-------------|--------|
| `total_commits` | All-time commit count | Git log |
| `commits_30d` | Commits in last 30 days | Git log |
| `branches` | Number of branches | Git branch |
| `contributors` | Unique committers | Git log |
| `open_issues` | Open GitHub issues | GitHub API |
| `closed_issues` | Closed GitHub issues | GitHub API |
| `open_prs` | Open pull requests | GitHub API |
| `merged_prs` | Merged pull requests | GitHub API |
| `lines_of_code` | Total lines (excl. comments) | cloc / tokei |
| `phi_cps` | Current φ-CPS value | ECOS_ROOT.json |
| `last_activity` | Last commit timestamp | Git log |
| `health_score` | Composite health (0-100) | Calculated |

### Global Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `total_repos` | Count of repositories | len(repositories) |
| `active_repos` | Repos with commits (30d) | WHERE commits_30d > 0 |
| `avg_phi_cps` | Average φ-CPS | SUM(phi_cps) / COUNT(*) |
| `total_commits` | Sum of all commits | SUM(total_commits) |
| `total_issues` | Sum of all issues | SUM(open + closed) |
| `cumulative_drift` | Total φ-CPS drift | phi_current - phi_genesis |
| `drift_percent` | Drift percentage | (cumulative_drift / phi_genesis) × 100 |

### Health Score Calculation

```python
def calculate_health_score(repo: Dict) -> float:
    """
    Calculate repository health score (0-100)
    
    Factors:
    - Recent activity (30 days): 30 points
    - Issue management: 20 points
    - PR velocity: 20 points
    - φ-CPS stability: 20 points
    - Documentation: 10 points
    """
    score = 0.0
    
    # Recent activity (commits in last 30 days)
    if repo['commits_30d'] > 0:
        score += min(30, repo['commits_30d'] * 3)
    
    # Issue management (closed / total)
    if repo['total_issues'] > 0:
        close_rate = repo['closed_issues'] / repo['total_issues']
        score += close_rate * 20
    
    # PR velocity (merged / total)
    if repo['total_prs'] > 0:
        merge_rate = repo['merged_prs'] / repo['total_prs']
        score += merge_rate * 20
    
    # φ-CPS stability (no excessive drift)
    phi_drift = abs(repo['phi_cps'] - 4.092)
    if phi_drift < 0.05:
        score += 20
    elif phi_drift < 0.10:
        score += 10
    
    # Documentation (README, docs/)
    if repo['has_readme']:
        score += 5
    if repo['has_docs']:
        score += 5
    
    return min(100.0, score)
```

---

## Visualization

### Chart Types

#### 1. φ-CPS Trend Line

**Purpose**: Visualize φ-CPS evolution over time  
**Type**: Line chart  
**X-axis**: Timeline (phases)  
**Y-axis**: φ-CPS value

```python
import matplotlib.pyplot as plt

phases = ['Genesis', '1A', '1B', '1D', '2A', '2B']
phi_values = [4.092, 4.127, 4.171, 4.202, 4.220, 4.226]

plt.plot(phases, phi_values, marker='o')
plt.axhline(y=4.092+0.05, color='r', linestyle='--', label='Threshold (+5%)')
plt.xlabel('Phase')
plt.ylabel('φ-CPS Value')
plt.title('φ-CPS Evolution')
plt.legend()
plt.savefig('phi_cps_trend.png')
```

#### 2. Repository Activity Bar Chart

**Purpose**: Compare commit activity across repos  
**Type**: Horizontal bar chart  
**X-axis**: Commit count  
**Y-axis**: Repository names

```python
import matplotlib.pyplot as plt

repos = ['KIVA-CLI', 'ECOYSTEM', 'DevTools', 'BRAIN']
commits = [19, 1, 0, 0]

plt.barh(repos, commits)
plt.xlabel('Commits')
plt.ylabel('Repository')
plt.title('Repository Activity (Last 30 Days)')
plt.savefig('repo_activity.png')
```

#### 3. φ-CPS Distribution Pie Chart

**Purpose**: Show drift contribution by phase  
**Type**: Pie chart  
**Segments**: Phase percentages

```python
import matplotlib.pyplot as plt

phases = ['Phase 1A', 'Phase 1B', 'Phase 1D', 'Phase 2A', 'Phase 2B']
drifts = [0.035, 0.044, 0.031, 0.018, 0.006]

plt.pie(drifts, labels=phases, autopct='%1.1f%%')
plt.title('φ-CPS Drift Distribution')
plt.savefig('phi_drift_distribution.png')
```

#### 4. Health Score Heatmap

**Purpose**: Visualize repo health across metrics  
**Type**: Heatmap  
**Rows**: Repositories  
**Columns**: Metric categories

```python
import seaborn as sns
import pandas as pd

data = {
    'Activity': [90, 30, 0, 0],
    'Issues': [100, 100, 100, 100],
    'PRs': [100, 100, 100, 100],
    'φ-CPS': [80, 100, 100, 100],
    'Docs': [100, 50, 50, 50]
}

df = pd.DataFrame(data, index=['KIVA-CLI', 'ECOYSTEM', 'DevTools', 'BRAIN'])
sns.heatmap(df, annot=True, cmap='YlGnBu')
plt.title('Repository Health Matrix')
plt.savefig('health_heatmap.png')
```

---

## Export Formats

### Markdown

**Default format**, human-readable, GitHub-compatible

**Features**:
- Tables for data
- Headers for sections
- Links to repos/commits
- Emoji for status

**Example**:
```markdown
## Repository Status

| Repo | Status | Commits |
|------|--------|----------|
| KIVA-CLI | ✅ ACTIVE | 19 |
| ECOYSTEM | ✅ ACTIVE | 1 |
```

### JSON

**Machine-readable format** for API integration

**Structure**:
```json
{
  "generated_at": "2026-02-28T18:00:00Z",
  "ecosystem_id": "ecosystem-1",
  "repositories": [
    {
      "name": "KIVA-CLI",
      "status": "ACTIVE",
      "phi_cps": 4.226,
      "commits": 19,
      "metrics": { /* ... */ }
    }
  ],
  "global_metrics": { /* ... */ }
}
```

### HTML

**Web-ready format** with styling and interactivity

**Features**:
- CSS styling (Bootstrap)
- Interactive charts (Chart.js)
- Responsive design
- Dark/light mode toggle
- Export to PDF button

**Template**:
```html
<!DOCTYPE html>
<html>
<head>
  <title>Ecosystem Metrics Dashboard</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <div class="container">
    <h1>Ecosystem-1 Dashboard</h1>
    <div class="row">
      <div class="col-md-6">
        <canvas id="phiCpsChart"></canvas>
      </div>
      <div class="col-md-6">
        <canvas id="activityChart"></canvas>
      </div>
    </div>
  </div>
  <script src="dashboard.js"></script>
</body>
</html>
```

---

## Automation

### GitHub Actions Integration

**Workflow**: `ecosystem_sync.yml`  
**Step**: Generate Metrics Dashboard

```yaml
- name: Generate Metrics Dashboard
  run: |
    python scripts/ecosystem_metrics_dashboard.py \
      --root . \
      --format markdown \
      --output metrics_dashboard.md
```

**Artifacts**:
```yaml
- name: Upload Metrics Dashboard
  uses: actions/upload-artifact@v4
  with:
    name: metrics-dashboard-${{ github.run_number }}
    path: metrics_dashboard.md
    retention-days: 30
```

### Scheduled Generation

**Cron**: Daily at 02:00 UTC (after sync)

```yaml
on:
  schedule:
    - cron: '0 2 * * *'
```

### Manual Trigger

```yaml
on:
  workflow_dispatch:
    inputs:
      dashboard_type:
        type: choice
        options:
          - overview
          - drift
          - compare
```

---

## Customization

### Custom Metrics

Add custom metrics to `ecosystem_metrics_dashboard.py`:

```python
class EcosystemMetrics:
    def collect_custom_metrics(self, repo_path: Path) -> Dict:
        """Collect custom repository metrics."""
        return {
            "test_coverage": self.get_test_coverage(repo_path),
            "code_quality_score": self.get_code_quality(repo_path),
            "dependency_count": self.get_dependency_count(repo_path)
        }
```

### Custom Dashboard Sections

Extend dashboard template:

```python
def generate_custom_section(self, data: Dict) -> str:
    """Generate custom dashboard section."""
    section = "## Custom Analysis\n\n"
    section += f"- Custom Metric 1: {data['custom1']}\n"
    section += f"- Custom Metric 2: {data['custom2']}\n"
    return section
```

### Custom Export Format

Add new export format:

```python
def export_to_csv(self, data: Dict, output_path: Path):
    """Export metrics to CSV format."""
    import csv
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Repository', 'φ-CPS', 'Commits'])
        
        for repo in data['repositories']:
            writer.writerow([repo['name'], repo['phi_cps'], repo['commits']])
```

---

## Support

**Documentation**: [KIVA-CLI README](../README.md)  
**Script**: `scripts/ecosystem_metrics_dashboard.py`  
**Issues**: [GitHub Issues](https://github.com/gerivdb/KIVA-CLI/issues)

---

**Generated by**: ECOS-AUTO H0 Autonomous System  
**Mode**: NO-HITL (Zero Human Interaction)  
**Version**: 1.0.0  
**Last Updated**: 2026-02-28
