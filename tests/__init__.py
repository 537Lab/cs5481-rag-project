"""Tests package.

Keeping an __init__.py lets `cli offline-demo` import the MOCK doubles from
tests.fakes, so there is exactly ONE copy of each test double in the repo.
Production commands (ingest / retrieve / ask) never import this package.
"""
