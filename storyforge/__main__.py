"""CLI entry: python -m imaginate "A brave fox..." """

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_orchestrator.orchestrator import main
main()
