#!/usr/bin/env python3
"""Entry point for running the pi_client app as a module"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Check if we should run in multi-printer mode
    if os.getenv("LABELBERRY_MULTI_PRINTER", "false").lower() == "true":
        logger.info("Starting in multi-printer mode")
        from .main_multi import start_server
        start_server()
    else:
        logger.info("Starting in single-printer mode")
        from .main import start_server
        start_server()
except Exception as e:
    logger.error(f"Failed to start LabelBerry service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)