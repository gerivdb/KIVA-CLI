#!/usr/bin/env python3
"""
WAL Database Backup Manager
Automated backup and restore for KIVA-CLI Global WAL database
"""

import os
import sqlite3
import gzip
import shutil
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import subprocess
import json

class WALBackupManager:
    """Manage WAL database backups with multiple strategies"""
    
    def __init__(self, db_path: str = "~/.kiva/global_wal.db"):
        self.db_path = Path(db_path).expanduser()
        self.backup_dir = Path("~/.kiva/backups/wal").expanduser()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.remote_repo = "gerivdb/ECOYSTEM"
        self.remote_path = "backups/wal"
        
    def create_backup(self, backup_type: str = "full") -> Dict:
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"wal_backup_{backup_type}_{timestamp}"
        backup_file = self.backup_dir / f"{backup_id}.db"
        compressed_file = self.backup_dir / f"{backup_id}.db.gz"
        
        try:
            # Create backup using SQLite backup API
            if backup_type == "full":
                shutil.copy2(self.db_path, backup_file)
            elif backup_type == "incremental":
                # Copy only new entries (simplified - real impl would use WAL segments)
                self._create_incremental_backup(backup_file)
            
            # Compress backup
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed backup
            backup_file.unlink()
            
            # Calculate checksum
            checksum = self._calculate_checksum(compressed_file)
            
            # Create metadata
            metadata = {
                "backup_id": backup_id,
                "backup_type": backup_type,
                "timestamp": timestamp,
                "size_bytes": compressed_file.stat().st_size,
                "checksum": checksum,
                "status": "SUCCESS"
            }
            
            # Save metadata
            metadata_file = self.backup_dir / f"{backup_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return metadata
            
        except Exception as e:
            return {
                "backup_id": backup_id,
                "backup_type": backup_type,
                "timestamp": timestamp,
                "status": "FAILED",
                "error": str(e)
            }
    
    def _create_incremental_backup(self, backup_file: Path):
        """Create incremental backup (simplified)"""
        # Real implementation would use SQLite WAL mode and copy only new segments
        shutil.copy2(self.db_path, backup_file)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def upload_to_github(self, backup_id: str) -> bool:
        """Upload backup to GitHub repository"""
        compressed_file = self.backup_dir / f"{backup_id}.db.gz"
        metadata_file = self.backup_dir / f"{backup_id}.json"
        
        if not compressed_file.exists() or not metadata_file.exists():
            return False
        
        try:
            # Use GitHub CLI to upload
            remote_backup_path = f"{self.remote_path}/{backup_id}.db.gz"
            remote_metadata_path = f"{self.remote_path}/{backup_id}.json"
            
            # Read files
            with open(compressed_file, 'rb') as f:
                backup_data = f.read()
            with open(metadata_file, 'r') as f:
                metadata = f.read()
            
            # Upload using git (simplified - real impl would use GitHub API)
            print(f"Would upload {compressed_file} to {self.remote_repo}/{remote_backup_path}")
            print(f"Would upload {metadata_file} to {self.remote_repo}/{remote_metadata_path}")
            
            return True
            
        except Exception as e:
            print(f"Upload failed: {e}")
            return False
    
    def restore_backup(self, backup_id: str, source: str = "local") -> bool:
        """Restore database from backup"""
        if source == "local":
            compressed_file = self.backup_dir / f"{backup_id}.db.gz"
        else:
            # Download from GitHub
            compressed_file = self._download_from_github(backup_id)
        
        if not compressed_file or not compressed_file.exists():
            return False
        
        try:
            # Create backup of current database
            current_backup = self.db_path.with_suffix('.db.pre_restore')
            shutil.copy2(self.db_path, current_backup)
            
            # Decompress and restore
            temp_file = self.db_path.with_suffix('.db.tmp')
            with gzip.open(compressed_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verify restored database
            if self._verify_database(temp_file):
                # Replace current database
                shutil.move(temp_file, self.db_path)
                return True
            else:
                # Restore failed, rollback
                temp_file.unlink()
                return False
                
        except Exception as e:
            print(f"Restore failed: {e}")
            # Rollback to pre-restore backup
            if current_backup.exists():
                shutil.copy2(current_backup, self.db_path)
            return False
    
    def _download_from_github(self, backup_id: str) -> Optional[Path]:
        """Download backup from GitHub"""
        # Simplified - real impl would use GitHub API
        return None
    
    def _verify_database(self, db_file: Path) -> bool:
        """Verify database integrity"""
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            return result == "ok"
        except Exception:
            return False
    
    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for backup_file in self.backup_dir.glob("wal_backup_*.db.gz"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                backup_file.unlink()
                # Remove corresponding metadata
                metadata_file = backup_file.with_suffix('.json')
                if metadata_file.exists():
                    metadata_file.unlink()
    
    def run_backup_cycle(self):
        """Execute complete backup cycle"""
        results = []
        
        # Full backup
        result = self.create_backup("full")
        results.append(result)
        
        if result["status"] == "SUCCESS":
            # Upload to GitHub
            self.upload_to_github(result["backup_id"])
        
        # Cleanup old backups
        self.cleanup_old_backups()
        
        return results


if __name__ == "__main__":
    manager = WALBackupManager()
    results = manager.run_backup_cycle()
    
    for result in results:
        print(f"Backup {result['backup_id']}: {result['status']}")
