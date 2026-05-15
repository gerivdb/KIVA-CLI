    def _find_by_content(self, base: Path, epic_id: str, discovered: Dict):
        """Find files containing EPIC references using BDCP-optimized search."""
        import subprocess

        search_terms = [epic_id, f"EPIC_{epic_id}"]
        # Only search in relevant file types and skip large files
        file_patterns = ["*.py", "*.md", "*.txt", "*.json", "*.yml", "*.yaml"]

        # BDCP Sprint 1: Direct ripgrep execution (true zero-overhead approach)
        try:
            # Single ripgrep command with all patterns and terms (BDCP: one process, zero inter-process)
            cmd = ['rg', '--files-with-matches',
                   '--max-filesize=1M',     # BDCP: No large file allocation
                   '--no-messages',         # BDCP: Silent operation
                   '--no-filename']         # BDCP: Direct output

            # Add search terms efficiently
            for term in search_terms:
                cmd.extend(['--regexp', term])

            # Add file patterns
            for pattern in file_patterns:
                cmd.extend(['--glob', pattern])

            cmd.append(str(base))

            # BDCP: Execute and process immediately (no intermediate storage)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                # BDCP: Process each line immediately, no lists or dictionaries
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            file_path = Path(line.strip())
                            if file_path.exists():
                                rel_path = str(file_path.relative_to(base))
                                # BDCP: Direct append, no categorization logic overhead
                                if 'test' in rel_path.lower():
                                    discovered['tests'].append(rel_path)
                                else:
                                    discovered['modules'].append(rel_path)
                        except (ValueError, OSError):
                            continue

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # BDCP Fallback: Minimal synchronous search (only epics/ directory)
            try:
                for file_path in base.glob(f"epics/*{epic_id}*"):
                    if file_path.is_file() and file_path.stat().st_size < 50 * 1024:  # Even smaller limit
                        rel_path = str(file_path.relative_to(base))
                        discovered['modules'].append(rel_path)
            except Exception:
                pass

        # BDCP: Optional deduplication only if needed (avoids set() allocation for small results)
        if len(discovered['tests']) > 10 or len(discovered['modules']) > 10:
            discovered['tests'] = list(set(discovered['tests']))
            discovered['modules'] = list(set(discovered['modules']))