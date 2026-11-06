import importlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
importlib.import_module(os.environ["KMOD"])
