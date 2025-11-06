"""
Build script to create Lambda deployment package
This packages the Songbird code + dependencies into lambda_deployment.zip
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
PACKAGE_DIR = SCRIPT_DIR / "lambda_package"
ZIP_FILE = SCRIPT_DIR / "lambda_deployment.zip"
SRC_DIR = PROJECT_ROOT / "src" / "songbird"
LAMBDA_HANDLER = SCRIPT_DIR / "lambda_function.py"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


def clean():
    """Remove old package directory and zip file"""
    print("Cleaning old build artifacts...")
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    if ZIP_FILE.exists():
        ZIP_FILE.unlink()


def install_dependencies():
    """Install Python dependencies to package directory"""
    print("Installing dependencies...")
    PACKAGE_DIR.mkdir(exist_ok=True)

    # Install requirements to package directory
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "-r", str(REQUIREMENTS),
        "-t", str(PACKAGE_DIR),
        "--quiet"
    ])

    print(f"   [OK] Dependencies installed to {PACKAGE_DIR}")


def copy_source_code():
    """Copy Songbird source code to package directory"""
    print("Copying source code...")

    # Copy songbird package
    dest_songbird = PACKAGE_DIR / "songbird"
    if dest_songbird.exists():
        shutil.rmtree(dest_songbird)
    shutil.copytree(SRC_DIR, dest_songbird)
    print(f"   [OK] Copied songbird package")

    # Copy Lambda handler
    shutil.copy2(LAMBDA_HANDLER, PACKAGE_DIR / "lambda_function.py")
    print(f"   [OK] Copied lambda_function.py")


def create_zip():
    """Create deployment zip file"""
    print("Creating deployment package...")

    # Create zip file
    shutil.make_archive(
        str(ZIP_FILE.with_suffix('')),
        'zip',
        str(PACKAGE_DIR)
    )

    # Get size
    size_mb = ZIP_FILE.stat().st_size / (1024 * 1024)
    print(f"   [OK] Created {ZIP_FILE.name} ({size_mb:.2f} MB)")


def main():
    """Main build process"""
    print("Building Lambda deployment package for Songbird\n")

    try:
        clean()
        install_dependencies()
        copy_source_code()
        create_zip()

        print("\n[SUCCESS] Build complete!")
        print(f"Deployment package: {ZIP_FILE}")
        print("\nNext steps:")
        print("  1. cd terraform")
        print("  2. terraform apply")

    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
