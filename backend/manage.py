#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ibms.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            'available on your PYTHONPATH environment variable?'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
# 2026-11-11T15:06:10Z entrypoint
