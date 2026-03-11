"""
Entrypoint script for PyInstaller to build rtgamma_cli without relative import issues.
"""
from rtgamma.main import main

if __name__ == '__main__':
    main()
