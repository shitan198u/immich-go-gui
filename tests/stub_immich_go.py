#!/usr/bin/env python3
"""Stub immich-go CLI executable for testing environment variable and argv delivery."""
import json
import os
import sys


def main():
    result = {
        "argv": sys.argv[1:],
        "env": {k: v for k, v in os.environ.items() if k.startswith("IMMICH_GO_")},
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
