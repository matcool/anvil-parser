"""
This is an utility script to add the parent folder to the path
so i can do `import anvil` in the examples
Code entirely from: https://stackoverflow.com/a/33532002/9124836
"""
from inspect import getsourcefile
import os.path
import sys

current_path = os.path.abspath(getsourcefile(lambda:0))
current_dir = os.path.dirname(current_path)
parent_dir = current_dir[:current_dir.rfind(os.path.sep)]

sys.path.insert(0, parent_dir)
