#!/usr/bin/env python3
"""Retired: treebank chunk ends must not be used to force annotation boundaries."""
import sys

if __name__ == '__main__':
    print('This tool is retired. The current schema annotates the smallest meaningful Arabic chunks;')
    print('treebank boundaries are diagnostic only and must not be injected into the annotation.')
    print('Use: python3 tools/chunker_report.py --annotations-dir <directory>')
    sys.exit(2)
