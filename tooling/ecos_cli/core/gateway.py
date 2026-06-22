"""
ECOS CLI Gateway
Delegates KIVA-specific commands from ECOS CLI to KIVA CLI
Maintains backward compatibility: ecos project init -> kiva project init
"""
from pathlib import Path
from typing import List, Optional, Dict
import subprocess
import json
import sys

class EcosGateway:
    """Gateway for delegating ECOS CLI commands to specialized CLIs"""
    
    DELEGATION_MAP = {
        "project": "kiva",
        "deploy": "kiva",
        "config": "kiva",
        "secrets": "kiva",
        "monitoring": "kiva",
        "rollback": "kiva",
        "health": "kiva",
        # Future delegations
        "pattern": "brain",
        "knowledge": "brain",
        "agent": "brain",
        "workflow": "fluence",
        "pipeline": "fluence",
        "execution": "fluence",
        "lint": "devtools",
        "test": "devtools",
        "coverage": "devtools"
    }
    
    def __init__(self, wal_manager=None):
        """
        Initialize ECOS Gateway
        
        Args:
            wal_manager: Global WAL Manager instance for logging
        """
        self.wal_manager = wal_manager
        self.cli_paths = self._discover_cli_executables()
    
    def _discover_cli_executables(self) -> Dict[str, Optional[Path]]:
        """Discover specialized CLI executables in ecosystem"""
        cli_paths = {}
        
        search_roots = [
            Path.cwd().parent,
            Path.home() / "Dev" / "ecosystem-1",
            Path("/opt/ecosystem-1")
        ]
        
        cli_map = {
            "kiva": ["KIVA-CLI/bin/kiva", "KIVA-CLI/kiva_cli/kiva.py"],
            "brain": ["BRAIN/bin/brain", "BRAIN/brain_cli/brain.py"],
            "fluence": ["FLUENCE/target/release/fluence", "FLUENCE/bin/fluence"],
            "devtools": ["DevTools/bin/devtools", "DevTools/devtools_cli/devtools.py"]
        }
        
        for cli_name, relative_paths in cli_map.items():
            found = None
            for root in search_roots:
                for rel_path in relative_paths:
                    candidate = root / rel_path
                    if candidate.exists():
                        found = candidate
                        break
                if found:
                    break
            
            cli_paths[cli_name] = found
        
        return cli_paths
    
    def delegate(
        self,
        command: str,
        args: List[str],
        timeout: int = 30
    ) -> Dict[str, any]:
        """
        Delegate command to specialized CLI
        
        Args:
            command: Command name (project, deploy, etc.)
            args: Command arguments
            timeout: Subprocess timeout in seconds
        
        Returns:
            Dict with status, output, target_cli
        """
        # Determine target CLI
        target_cli = self.DELEGATION_MAP.get(command)
        
        if not target_cli:
            return {
                "status": "UNKNOWN_COMMAND",
                "command": command,
                "error": f"No delegation mapping for command: {command}",
                "available": list(self.DELEGATION_MAP.keys())
            }
        
        cli_path = self.cli_paths.get(target_cli)
        
        if not cli_path:
            return {
                "status": "CLI_NOT_FOUND",
                "target_cli": target_cli,
                "error": f"{target_cli.upper()} CLI not found in ecosystem",
                "search_paths": [str(p) for p in self.cli_paths.values() if p]
            }
        
        # Construct subprocess command
        if cli_path.suffix == ".py":
            cmd = [sys.executable, str(cli_path), command] + args
        else:
            cmd = [str(cli_path), command] + args
        
        # Log delegation in WAL
        if self.wal_manager:
            self.wal_manager.append_event(
                service_name="ecos-cli-gateway",
                event_type="DELEGATION",
                payload={
                    "command": command,
                    "target_cli": target_cli,
                    "args": args
                }
            )
        
        # Execute delegation
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            result = {
                "status": "SUCCESS" if proc.returncode == 0 else "FAILED",
                "target_cli": target_cli,
                "command": command,
                "return_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }
            
            # Parse JSON output if available
            try:
                if proc.stdout.strip().startswith("{"):
                    result["output"] = json.loads(proc.stdout)
            except:
                pass
            
            return result
        
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "target_cli": target_cli,
                "command": command,
                "timeout": timeout,
                "error": f"Command exceeded {timeout}s timeout"
            }
        
        except Exception as e:
            return {
                "status": "ERROR",
                "target_cli": target_cli,
                "command": command,
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, any]:
        """Check health of all delegated CLIs"""
        health_status = {}
        
        for cli_name, cli_path in self.cli_paths.items():
            if not cli_path:
                health_status[cli_name] = {
                    "status": "NOT_FOUND",
                    "available": False
                }
                continue
            
            # Try version check
            try:
                if cli_path.suffix == ".py":
                    cmd = [sys.executable, str(cli_path), "--version"]
                else:
                    cmd = [str(cli_path), "--version"]
                
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                health_status[cli_name] = {
                    "status": "HEALTHY" if proc.returncode == 0 else "UNHEALTHY",
                    "available": True,
                    "path": str(cli_path),
                    "version": proc.stdout.strip() if proc.returncode == 0 else None
                }
            
            except Exception as e:
                health_status[cli_name] = {
                    "status": "ERROR",
                    "available": False,
                    "error": str(e)
                }
        
        return {
            "timestamp": self._get_timestamp(),
            "cli_status": health_status,
            "total_available": sum(1 for s in health_status.values() if s.get("available"))
        }
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get ISO8601 timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Example usage in ECOS CLI
def integrate_gateway_in_ecos_cli():
    """
    Integration example for ECOS CLI main script
    
    Add to ECOYSTEM/tooling/ecos_cli/main.py:
    
    from tooling.ecos_cli.core.gateway import EcosGateway
    
    # Initialize gateway
    gateway = EcosGateway(wal_manager=global_wal_manager)
    
    # Delegate project commands
    if args.command in gateway.DELEGATION_MAP:
        result = gateway.delegate(args.command, args.remaining_args)
        
        if result["status"] == "SUCCESS":
            print(result["stdout"])
            sys.exit(0)
        else:
            print(f"Error: {result.get('error', result.get('stderr'))}", file=sys.stderr)
            sys.exit(result.get("return_code", 1))
    """
    pass
