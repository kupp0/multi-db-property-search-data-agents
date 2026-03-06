import time
import asyncio
from unittest.mock import MagicMock
import os

# Create mock objects
class MockDatabase:
    pass

class MockInstance:
    def database(self, db_id):
        return MockDatabase()

class MockClient:
    def __init__(self, project=None):
        pass
    def instance(self, instance_id):
        return MockInstance()

# Original implementation
spanner_client_orig = None
def get_spanner_db_orig():
    global spanner_client_orig
    if not spanner_client_orig:
        spanner_client_orig = MockClient(project="test_project")
    instance = spanner_client_orig.instance("test_instance")
    database = instance.database("test_db")
    return database

# Optimized implementation
spanner_client_opt = None
spanner_db_opt = None
def get_spanner_db_opt():
    global spanner_client_opt, spanner_db_opt
    if not spanner_db_opt:
        if not spanner_client_opt:
            spanner_client_opt = MockClient(project="test_project")
        instance = spanner_client_opt.instance("test_instance")
        spanner_db_opt = instance.database("test_db")
    return spanner_db_opt

def run_benchmark():
    n_iters = 1000000

    # Warm up
    get_spanner_db_orig()
    get_spanner_db_opt()

    start = time.perf_counter()
    for _ in range(n_iters):
        get_spanner_db_orig()
    orig_time = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(n_iters):
        get_spanner_db_opt()
    opt_time = time.perf_counter() - start

    print(f"Original: {orig_time:.4f}s")
    print(f"Optimized: {opt_time:.4f}s")
    print(f"Improvement: {(orig_time - opt_time) / orig_time * 100:.2f}%")

if __name__ == "__main__":
    run_benchmark()
