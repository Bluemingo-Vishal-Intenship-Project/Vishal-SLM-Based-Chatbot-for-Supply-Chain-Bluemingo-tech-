"""
Build script to create .exe file for the desktop application.
Run: python build_desktop_exe.py
"""

import PyInstaller.__main__
import os
import shutil
import sys

def build_exe():
    """Build the .exe file for desktop application."""
    print("="*60)
    print("Excel/CSV to RAG System - Desktop App Builder")
    print("="*60)
    print("\nThis will create a standalone .exe file for the desktop application.")
    print("Note: This may take 10-30 minutes and create a large file (~500MB-1GB)")
    print("      because it bundles all ML models and dependencies.\n")
    
    response = input("Continue? (y/n): ").strip().lower()
    if response != 'y':
        print("Build cancelled.")
        return
    
    # Clean previous builds
    print("\nCleaning previous builds...")
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('Excel_RAG_Desktop.spec'):
        os.remove('Excel_RAG_Desktop.spec')
    
    print("Building .exe file...")
    print("This may take a while, please be patient...\n")
    
    try:
        PyInstaller.__main__.run([
            'desktop_app.py',
            '--name=Excel_RAG_Desktop',
            '--onefile',
            '--windowed',
            '--hidden-import=tkinter',
            '--hidden-import=excel_to_rag',
            '--hidden-import=pandas',
            '--hidden-import=openpyxl',
            '--hidden-import=xlrd',
            '--hidden-import=chromadb',
            '--hidden-import=sentence_transformers',
            '--hidden-import=numpy',
            '--collect-all=sentence_transformers',
            '--collect-all=chromadb',
            '--collect-all=transformers',
            '--collect-all=torch',
            '--collect-all=sklearn',
            '--noconsole',
            '--clean'
        ])
        
        print("\n" + "="*60)
        print("✓ Build complete!")
        print("="*60)
        print("\nYour .exe file is in the 'dist' folder:")
        print("  dist/Excel_RAG_Desktop.exe")
        print("\nYou can now:")
        print("  1. Run the .exe file directly (double-click)")
        print("  2. Distribute it to others")
        print("  3. No installation needed - just run!")
        print("\nNote: The first run may take longer as it initializes the model.")
        
    except Exception as e:
        print(f"\n✗ Build failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure PyInstaller is installed: pip install pyinstaller")
        print("  2. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("  3. Try running as administrator")
        sys.exit(1)


if __name__ == '__main__':
    build_exe()














