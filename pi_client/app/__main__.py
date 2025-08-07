#!/usr/bin/env python3
"""Entry point for running the pi_client app as a module"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# Check if we should run in multi-printer mode
if os.getenv("LABELBERRY_MULTI_PRINTER", "false").lower() == "true":
    logger.info("Starting in multi-printer mode")
    from .main_multi import start_server
    start_server()
else:
    logger.info("Starting in single-printer mode")
    from .main import start_server
    if hasattr(start_server, '__call__'):
        start_server()
    else:
        # If main.py doesn't have start_server, run it directly
        import uvicorn
        from .main import app
        uvicorn.run(app, host="0.0.0.0", port=8000)