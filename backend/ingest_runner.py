# backend/ingest_runner.py
import sys
from pathlib import Path
from vector_store import ingest_files

def main(paths):
    abs_paths = [str(Path(p).resolve()) for p in paths]
    result = ingest_files(abs_paths)
    print("Ingest result:", result)

if __name__ == "__main__":
    # Example usage:
    # python backend/ingest_runner.py assets/checkout.html docs/product_specs.md
    if len(sys.argv) < 2:
        print("Usage: python backend/ingest_runner.py <file1> [file2 ...]")
    else:
        main(sys.argv[1:])
