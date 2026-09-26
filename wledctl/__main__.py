"""Allows `python3 -m wledctl ...`"""
import sys
from .app import main

sys.exit(main())
