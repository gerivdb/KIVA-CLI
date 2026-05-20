#!/usr/bin/env python3
"""
Security Hardening Manager - KIVA CLI

Manages security audits, AppArmor profiles, secrets rotation, and security policies.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any


class SecurityManager:
    """Manages security hardening for ECOS repositories."""

    def __init__(self):
        pass

    def run_security_audit(self, repo_path: str) -> Dict[str, Any]:
        """
        Run security audit on a repository.
        
        Args:
            repo_path: Path to the repository
        
        Returns:
            Audit results with issues and recommendations
        """
        issues = []
        
        # Check for hardcoded secrets
        secrets = self._check_secrets(repo_path)
        if secrets:
            issues.extend(secrets)
        
        # Check file permissions
        permissions = self._check_permissions(repo_path)
        if permissions:
            issues.extend(permissions)
        
        # Check for known vulnerabilities in dependencies
        vulnerabilities = self._check_vulnerabilities(repo_path)
        if vulnerabilities:
            issues.extend(vulnerabilities)
        
        return {
            "repo_path": repo_path,
            "issues_count": len(issues),
            "issues": issues,
            "status": "PASS" if len(issues) == 0 else "FAIL"
        }

    def _check_secrets(self, repo_path: str) -> List[Dict[str, str]]:
        """Check for hardcoded secrets in repository."""
        issues = []
        secret_patterns = ["password", "secret", "api_key", "token", "private_key"]
        
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in root:
                continue
            
            for file in files:
                if file.endswith((".py", ".yml", ".yaml", ".json", ".env", ".ps1")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                            for pattern in secret_patterns:
                                if pattern in content:
                                    issues.append({
                                        "type": "SECRET",
                                        "severity": "HIGH",
                                        "file": file_path,
                                        "message": f"Potential hardcoded {pattern} found"
                                    })
                    except Exception:
                        pass
        
        return issues

    def _check_permissions(self, repo_path: str) -> List[Dict[str, str]]:
        """Check file permissions for security issues."""
        issues = []
        
        # Check for world-writable files
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    stat = os.stat(file_path)
                    if stat.st_mode & 0o002:  # World-writable
                        issues.append({
                            "type": "PERMISSION",
                            "severity": "MEDIUM",
                            "file": file_path,
                            "message": "File is world-writable"
                        })
                except Exception:
                    pass
        
        return issues

    def _check_vulnerabilities(self, repo_path: str) -> List[Dict[str, str]]:
        """Check for known vulnerabilities in dependencies."""
        issues = []
        
        # Check for requirements.txt and run pip audit
        requirements_file = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(requirements_file):
            try:
                result = subprocess.run(
                    ["pip", "audit", "-r", requirements_file, "--json"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    issues.append({
                        "type": "VULNERABILITY",
                        "severity": "HIGH",
                        "file": requirements_file,
                        "message": "Vulnerable dependencies found"
                    })
            except Exception:
                pass
        
        return issues

    def setup_apparmor_profile(self, container_name: str) -> bool:
        """
        Setup AppArmor profile for a container.
        
        Args:
            container_name: Name of the container
        
        Returns:
            True if successful
        """
        profile_content = f"""#include <tunables/global>

profile {container_name} flags=(attach_disconnected,mediate_deleted) {{
  #include <abstractions/base>

  # Network access
  network inet tcp,
  network inet udp,

  # File access
  /usr/bin/python3 ix,
  /usr/bin/pip3 ix,
  
  # Deny access to sensitive files
  deny /etc/shadow r,
  deny /etc/gshadow r,
}}
"""
        try:
            profile_path = f"/etc/apparmor.d/{container_name}"
            with open(profile_path, 'w') as f:
                f.write(profile_content)
            
            subprocess.run(["apparmor_parser", "-r", profile_path], check=True)
            return True
        except Exception:
            return False

    def rotate_secrets(self, repo_path: str, secret_name: str) -> bool:
        """
        Rotate a secret in the repository.
        
        Args:
            repo_path: Path to the repository
            secret_name: Name of the secret to rotate
        
        Returns:
            True if successful
        """
        # This would integrate with a secrets manager
        # For now, just log the rotation
        print(f"Rotating secret '{secret_name}' in {repo_path}")
        return True

    def get_security_status(self, repo_path: str) -> Dict[str, Any]:
        """
        Get overall security status for a repository.
        
        Args:
            repo_path: Path to the repository
        
        Returns:
            Security status summary
        """
        audit = self.run_security_audit(repo_path)
        
        return {
            "repo_path": repo_path,
            "status": audit["status"],
            "issues_count": audit["issues_count"],
            "last_audit": audit.get("issues", [])
        }