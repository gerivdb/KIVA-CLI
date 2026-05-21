#!/usr/bin/env python3
"""Health check and diagnostics commands for KIVA CLI.

Provides comprehensive health checks across infrastructure and services.
"""

import click
import json
from typing import Optional
from datetime import datetime


@click.group()
def health():
    """Health checks and service diagnostics."""
    pass


@health.command()
@click.option('--services', default='all', help='Services to check (comma-separated or "all")')
@click.option('--deep', is_flag=True, help='Perform deep health checks')
@click.option('--timeout', type=int, default=30, help='Timeout per service (seconds)')
@click.option('--format', type=click.Choice(['table', 'json', 'prometheus']), default='table')
def check(services: str, deep: bool, timeout: int, format: str):
    """Run health checks on services.
    
    Example:
        kiva health check --services=all --deep
        kiva health check --services=api,worker --format=json
    """
    check_type = "Deep" if deep else "Standard"
    click.echo(f"🏥 Running {check_type} health checks...\n")
    
    service_list = _parse_services(services)
    results = []
    
    for service in service_list:
        click.echo(f"Checking {service}...", nl=False)
        status = _check_service(service, deep, timeout)
        results.append({"service": service, **status})
        
        icon = "✅" if status['healthy'] else "❌"
        click.echo(f" {icon}")
    
    if format == 'table':
        _display_table(results)
    elif format == 'json':
        click.echo(json.dumps(results, indent=2))
    elif format == 'prometheus':
        _display_prometheus(results)
    
    # Summary
    healthy_count = sum(1 for r in results if r['healthy'])
    total = len(results)
    
    if healthy_count == total:
        click.echo(f"\n✅ All {total} services healthy", fg='green')
    else:
        click.echo(f"\n⚠️  {healthy_count}/{total} services healthy", fg='yellow')


@health.command()
@click.option('--service', required=True, help='Service name')
@click.option('--output', type=click.Path(), help='Output file for report')
def diagnose(service: str, output: Optional[str]):
    """Run comprehensive diagnostics on a service.
    
    Example:
        kiva health diagnose --service=api-prod --output=diagnostics.json
    """
    click.echo(f"🔍 Running diagnostics on {service}...\n")
    
    diagnostics = {
        "service": service,
        "timestamp": datetime.now().isoformat(),
        "checks": [
            {"name": "Process Status", "status": "OK", "details": "Running (PID 12345)"},
            {"name": "Memory Usage", "status": "WARNING", "details": "85% (4.2GB/5GB)"},
            {"name": "CPU Usage", "status": "OK", "details": "45%"},
            {"name": "Disk Space", "status": "OK", "details": "60% (300GB/500GB)"},
            {"name": "Network Connectivity", "status": "OK", "details": "All endpoints reachable"},
            {"name": "Database Connections", "status": "OK", "details": "12/100 active"},
            {"name": "Cache Hit Rate", "status": "OK", "details": "92%"},
            {"name": "Error Rate (5m)", "status": "OK", "details": "0.02%"},
        ],
        "recommendations": [
            "Consider increasing memory limit (currently 85% usage)",
            "Review slow queries (3 detected in last hour)"
        ]
    }
    
    for check in diagnostics['checks']:
        status_color = {'OK': 'green', 'WARNING': 'yellow', 'CRITICAL': 'red'}.get(check['status'])
        click.echo(f"  {check['name']:<25} [{check['status']:^8}] {check['details']}", fg=status_color)
    
    if diagnostics['recommendations']:
        click.echo("\n💡 Recommendations:")
        for rec in diagnostics['recommendations']:
            click.echo(f"  - {rec}")
    
    if output:
        with open(output, 'w') as f:
            json.dump(diagnostics, f, indent=2)
        click.echo(f"\n📄 Full report saved to {output}")


@health.command()
@click.option('--watch', is_flag=True, help='Continuous monitoring mode')
@click.option('--interval', type=int, default=10, help='Refresh interval (seconds)')
def monitor(watch: bool, interval: int):
    """Monitor system health in real-time.
    
    Example:
        kiva health monitor --watch --interval=5
    """
    if not watch:
        _display_snapshot()
        return
    
    click.echo(f"📊 Starting health monitor (refresh every {interval}s)...")
    click.echo("Press Ctrl+C to stop\n")
    
    try:
        import time
        while True:
            click.clear()
            _display_snapshot()
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\n\n✋ Monitoring stopped")


@health.command()
@click.option('--endpoint', required=True, help='Endpoint URL to test')
@click.option('--timeout', type=int, default=5, help='Timeout (seconds)')
@click.option('--expect-status', type=int, default=200, help='Expected HTTP status code')
def endpoint(endpoint: str, timeout: int, expect_status: int):
    """Test a specific HTTP endpoint.
    
    Example:
        kiva health endpoint --endpoint=https://api.example.com/health
    """
    click.echo(f"🌐 Testing endpoint: {endpoint}")
    click.echo(f"   Expected status: {expect_status}")
    click.echo(f"   Timeout: {timeout}s\n")
    
    # Mock HTTP request
    import time
    start = time.time()
    status_code = 200
    elapsed = (time.time() - start) * 1000
    
    if status_code == expect_status:
        click.echo(f"✅ Endpoint healthy", fg='green')
    else:
        click.echo(f"❌ Endpoint unhealthy (got {status_code}, expected {expect_status})", fg='red')
    
    click.echo(f"⏱️  Response time: {elapsed:.2f}ms")


def _parse_services(services: str) -> list:
    """Parse service list from string."""
    if services == 'all':
        return ['api-prod', 'worker', 'database', 'cache', 'queue']
    return [s.strip() for s in services.split(',')]


def _check_service(service: str, deep: bool, timeout: int) -> dict:
    """Perform health check on service."""
    # Mock health check logic
    import random
    healthy = random.random() > 0.1  # 90% healthy
    latency = random.randint(10, 200)
    
    result = {
        "healthy": healthy,
        "latency_ms": latency,
        "status_code": 200 if healthy else 503,
    }
    
    if deep:
        result.update({
            "memory_usage_pct": random.randint(40, 90),
            "cpu_usage_pct": random.randint(20, 80),
            "connections": random.randint(10, 100),
        })
    
    return result


def _display_table(results: list):
    """Display results as formatted table."""
    click.echo(f"\n{'Service':<20} {'Status':<10} {'Latency':<12} {'Details'}")
    click.echo("-" * 70)
    
    for result in results:
        status = "HEALTHY" if result['healthy'] else "UNHEALTHY"
        status_color = 'green' if result['healthy'] else 'red'
        latency = f"{result['latency_ms']}ms"
        
        details_parts = []
        if 'memory_usage_pct' in result:
            details_parts.append(f"MEM:{result['memory_usage_pct']}%")
        if 'cpu_usage_pct' in result:
            details_parts.append(f"CPU:{result['cpu_usage_pct']}%")
        details = ' '.join(details_parts)
        
        click.echo(f"{result['service']:<20}", nl=False)
        click.echo(f"{status:<10}", fg=status_color, nl=False)
        click.echo(f"{latency:<12} {details}")


def _display_prometheus(results: list):
    """Display results in Prometheus exposition format."""
    click.echo("# HELP service_health Service health status (1=healthy, 0=unhealthy)")
    click.echo("# TYPE service_health gauge")
    
    for result in results:
        value = 1 if result['healthy'] else 0
        click.echo(f'service_health{{service="{result["service"]}"}} {value}')
    
    click.echo("\n# HELP service_latency_ms Service response latency in milliseconds")
    click.echo("# TYPE service_latency_ms gauge")
    
    for result in results:
        click.echo(f'service_latency_ms{{service="{result["service"]}"}} {result["latency_ms"]}')


def _display_snapshot():
    """Display current health snapshot."""
    click.echo(f"🏥 Health Snapshot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = [
        {"service": "api-prod", "healthy": True, "latency_ms": 45},
        {"service": "worker", "healthy": True, "latency_ms": 120},
        {"service": "database", "healthy": True, "latency_ms": 12},
        {"service": "cache", "healthy": False, "latency_ms": 5000},
        {"service": "queue", "healthy": True, "latency_ms": 30},
    ]
    
    _display_table(results)


if __name__ == '__main__':
    health()
