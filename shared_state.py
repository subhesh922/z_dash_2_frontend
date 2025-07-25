# shared_state.py

from threading import Lock

class SharedState:
    """
    Thread-safe container to hold shared state across analysis pipeline.
    Used mainly for:
    - Storing structured metrics
    - Storing generated report parts
    """
    def __init__(self):
        self.lock = Lock()
        self.metrics = None
        self.report_parts = {}

shared_state = SharedState()
