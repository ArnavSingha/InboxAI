
import sys
import pytest

def main():
    print("\n🧪 InboxAI Automated Test Suite")
    print("=================================")
    print("Running core logic tests...\n")
    
    # Run pytest on the tests folder
    # -v: verbose
    # --tb=short: shorter traceback for readability
    with open("test_metrics.log", "w") as f:
        # Redirect stdout/stderr to file
        sys.stdout = f
        sys.stderr = f
        result = pytest.main(["-v", "--tb=short", "tests/test_core_logic.py"])
    
    # Restore stdout
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    print("\n=================================")
    if result == 0:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"❌ SOME TESTS FAILED (See test_metrics.log)")
        sys.exit(1)

if __name__ == "__main__":
    main()
