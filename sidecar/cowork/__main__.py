"""Entry point for running the sidecar as a standalone process."""

import asyncio
import sys

from cowork.rpc.server import RPCServer


def main():
    """Start the JSON-RPC server on stdin/stdout."""
    server = RPCServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
