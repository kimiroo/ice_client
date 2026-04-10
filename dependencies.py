import subprocess
import sys

def is_venv():
    return sys.base_prefix != sys.prefix

def is_dependencies_installed():
    try:
        import aiohttp
        import obsws_python
        import psutil
        import PySide6
        import socketio
        return True
    except:
        return False

def install_dependencies():
    try:
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        print('Dependencies installed successfully.')
    except subprocess.CalledProcessError as e:
        print(f'Error installing dependencies: {e}')
    except Exception as e:
        print(f'Unknown error occurred while installing dependencies: {e}')

print('Checking for dependencies...')

if not is_dependencies_installed():
    print('Dependencies not found. Installing...')
    install_dependencies()
else:
    print('Dependencies found.')