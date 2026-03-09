"""
Entrypoint script for PyInstaller to build rtgamma_cli without relative import issues.
"""
# Explicitly import for PyInstaller dependency tracking
import scipy.special
import PIL.Image
from rtgamma.main import main

if __name__ == '__main__':
    main()
