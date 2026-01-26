import signal

import uvicorn


class GracefulShutdown:
    """Handle graceful shutdown of multiple services."""

    def __init__(self):
        self.shutdown = False

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown = True


if __name__ == "__main__":
    shutdown_handler = GracefulShutdown()

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)
    signal.signal(signal.SIGINT, shutdown_handler.signal_handler)

    from app import app

    print("Starting Flask server with uvicorn...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        interface="wsgi"
    )
