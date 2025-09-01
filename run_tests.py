#!/usr/bin/env python3
"""
Test runner for Cloudflare Manager
Usage: python run_tests.py [options]
"""
import sys
import subprocess
import os

def run_tests():
    """Run the test suite with pytest."""
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Run pytest with common options
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',              # Verbose output
        '--tb=short',      # Short traceback format
        '--strict-markers', # Strict marker checking
        '--disable-warnings', # Disable deprecation warnings
    ]
    
    print("Running Cloudflare Manager test suite...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {result.returncode}")
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)