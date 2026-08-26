#!/usr/bin/env python3
"""
KIVA-CLI Fast Validation Script
Validation rapide pour le développement - vérifie l'environnement en < 10 secondes
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

def get_kiva_cli_root() -> Path:
    """Get KIVA-CLI root directory."""
    return Path(os.environ.get('KIVA_CLI_PATH', 'D:/DO/WEB/TOOLS/L1-INFRA/KIVA-CLI'))

def print_header(title: str, char: str = '=', length: int = 80):
    """Print formatted header."""
    print(f'\n{char * length}')
    print(f'{title.center(length)}')
    print(f'{char * length}\n')

def check_python_environment() -> Dict[str, bool]:
    """Check Python version and key modules."""
    print('Checking Python environment...')
    
    checks = {}
    
    # Python version
    try:
        version = sys.version_info
        checks['python_version'] = version >= (3, 8)
        print(f'   Python {version.major}.{version.minor}.{version.micro}: {checks["python_version"]}')
    except Exception as e:
        checks['python_version'] = False
        print(f'   Python check failed: {e}')
    
    # Key modules
    modules_to_check = ['json', 'pathlib', 'subprocess', 'sys', 'os', 'time']
    for module in modules_to_check:
        try:
            __import__(module)
            checks[f'module_{module}'] = True
            print(f'   Module {module}: Available')
        except ImportError:
            checks[f'module_{module}'] = False
            print(f'   Module {module}: Missing')
    
    return checks

def check_kiva_directory_structure() -> Dict[str, bool]:
    """Check KIVA-CLI directory structure."""
    print('\nChecking KIVA-CLI directory structure...')
    
    kiva_root = get_kiva_cli_root()
    checks = {}
    
    required_dirs = [
        '.kiva',
        '.kiva/pipelines', 
        'kiva_cli/core',
        'scripts',
        '.github/workflows'
    ]
    
    for dir_path in required_dirs:
        full_path = kiva_root / dir_path
        exists = full_path.exists() and full_path.is_dir()
        checks[f'dir_{dir_path.replace("/", "_")}'] = exists
        status = 'OK' if exists else 'MISSING'
        print(f'   {status} {dir_path}')
    
    return checks

def check_kiva_cli_pipelines() -> Dict[str, bool]:
    """Check KIVA-CLI pipeline YAML files."""
    print('\nChecking KIVA-CLI pipeline YAML files...')
    
    kiva_root = get_kiva_cli_root()
    pipelines_dir = kiva_root / '.kiva' / 'pipelines'
    
    if not pipelines_dir.exists():
        print('   Pipelines directory not found')
        return {'directory_exists': False}
    
    checks = {}
    
    yaml_files = list(pipelines_dir.glob('*.yaml'))
    checks['yaml_files_exist'] = len(yaml_files) > 0
    
    if yaml_files:
        print(f'   Found {len(yaml_files)} pipeline YAML files:')
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    content = f.read()
                    has_name = 'name:' in content
                    has_version = 'version:' in content
                    yaml_valid = has_name and has_version
                    status = 'OK' if yaml_valid else 'WARN'
                    print(f'      {status} {yaml_file.name} (name: {has_name}, version: {has_version})')
                    checks[f'pipeline_{yaml_file.stem}'] = yaml_valid
            except Exception as e:
                print(f'      ERROR {yaml_file.name}: {e}')
                checks[f'pipeline_{yaml_file.stem}'] = False
    
    return checks

def run_quick_validation() -> Dict[str, bool]:
    """Run quick validation tests."""
    print('\nRunning quick validation tests...')
    
    checks = {}
    
    # Test KIVA-CLI path
    try:
        kiva_root = get_kiva_cli_root()
        if kiva_root.exists():
            print(f'   OK KIVA-CLI path found: {kiva_root}')
            checks['path_exists'] = True
        else:
            print(f'   MISSING KIVA-CLI path not found: {kiva_root}')
            checks['path_exists'] = False
    except Exception as e:
        print(f'   ERROR KIVA-CLI path check failed: {e}')
        checks['path_exists'] = False
    
    # Test scripts directory
    scripts_dir = get_kiva_cli_root() / 'scripts'
    if scripts_dir.exists():
        script_count = len(list(scripts_dir.glob('*.py')))
        print(f'   OK Scripts directory found with {script_count} Python scripts')
        checks['scripts_dir'] = True
    else:
        print(f'   MISSING Scripts directory not found')
        checks['scripts_dir'] = False
    
    # Test core module
    core_dir = get_kiva_cli_root() / 'kiva_cli' / 'core'
    if core_dir.exists():
        core_files = list(core_dir.glob('*.py'))
        print(f'   OK Core module found with {len(core_files)} Python files')
        checks['core_module'] = True
    else:
        print(f'   MISSING Core module not found')
        checks['core_module'] = False
    
    return checks

def generate_validation_report(results: Dict[str, Dict], output_file: Optional[str] = None) -> str:
    """Generate validation report and optionally save to file."""
    print('\nGenerating validation report...')
    
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'validation_type': 'KIVA-CLI_Fast_Validation',
        'results': {},
        'summary': {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'success_rate': 0.0
        }
    }
    
    for test_name, results_dict in results.items():
        report['results'][test_name] = results_dict
        
        total_checks = len(results_dict)
        passed_checks = sum(1 for v in results_dict.values() if v is True)
        failed_checks = sum(1 for v in results_dict.values() if v is False)
        
        report['summary']['total_checks'] += total_checks
        report['summary']['passed_checks'] += passed_checks
        report['summary']['failed_checks'] += failed_checks
    
    if report['summary']['total_checks'] > 0:
        report['summary']['success_rate'] = (report['summary']['passed_checks'] / 
                                           report['summary']['total_checks']) * 100
    
    print('\n   Validation Summary:')
    for test_name, results_dict in results.items():
        passed = sum(1 for v in results_dict.values() if v is True)
        total = len(results_dict)
        status = 'PASS' if passed == total else 'FAIL'
        print(f'   {test_name}: {passed}/{total} {status}')
    
    print(f'\n   Overall Success Rate: {report["summary"]["success_rate"]:.1f}%')
    print(f'   Checks Passed: {report["summary"]["passed_checks"]}/{report["summary"]["total_checks"]}')
    
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f'   Report saved: {output_file}')
        except Exception as e:
            print(f'   Could not save report: {e}')
    
    return json.dumps(report, indent=2)

def main():
    """Main validation function."""
    print_header('KIVA-CLI Fast Validation - Development Environment Check')
    
    results = {}
    
    # Run all checks
    results['python_environment'] = check_python_environment()
    results['directory_structure'] = check_kiva_directory_structure()
    results['pipeline_check'] = check_kiva_cli_pipelines()
    results['quick_validation'] = run_quick_validation()
    
    # Overall status
    overall_success = all(
        all(v is True for v in test_results.values()) if test_results else True 
        for test_results in results.values()
    )
    
    status_icon = 'OK' if overall_success else 'FAIL'
    print(f'\n{status_icon} Overall validation status: {"PASS" if overall_success else "FAIL"}')
    
    # Generate report
    report_file = str(get_kiva_cli_root() / 'validation_report.json')
    generate_validation_report(results, report_file)
    
    print(f'\nValidation complete!')
    print(f'   KIVA-CLI root: {get_kiva_cli_root()}')
    print(f'   Report: {report_file}')
    
    if not overall_success:
        print('\nSome validation checks failed. Please review results above.')
        sys.exit(1)
    else:
        print('\nAll validation checks passed! KIVA-CLI is ready for development.')
        sys.exit(0)

if __name__ == '__main__':
    main()