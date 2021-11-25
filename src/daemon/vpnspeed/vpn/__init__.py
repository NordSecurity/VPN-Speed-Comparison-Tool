# Ensure that all implementations are loaded into dynamic
import importlib
import os
import glob


modules = [
    os.path.basename(f)[:-3]
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
    if os.path.basename(f) not in {"__init__.py", "dynamic.py", "multi.py"}
]
for module in modules:
    importlib.import_module(__name__ + "." + module)


from .dynamic import DynamicVPN, VPNSession
