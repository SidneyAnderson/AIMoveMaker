#!/usr/bin/env python3
"""
Lightweight CI test for Phase 0 scripts.
Tests that scripts can be imported and schema is valid JSON (no GPU required).
"""
import sys
import json
from pathlib import Path

def test_imports():
    """Test that Phase 0 scripts can be imported (CPU-only syntax check)."""
    print("Testing Phase 0 script imports (no GPU)...")
    
    # Import scripts to check syntax
    try:
        # These imports should work even without GPU
        sys.path.insert(0, str(Path(__file__).parent))
        
        import env_check
        print("  ✅ env_check.py imports OK")
        
        import vram_fit
        print("  ✅ vram_fit.py imports OK")
        
        import converter_check
        print("  ✅ converter_check.py imports OK")
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False
    
    return True

def test_schema():
    """Test that schema.json is valid."""
    print("Testing results schema...")
    
    schema_path = Path(__file__).parent / "results" / "schema.json"
    try:
        with open(schema_path) as f:
            schema = json.load(f)
        
        # Basic validation
        assert "$schema" in schema, "Missing $schema field"
        assert "properties" in schema, "Missing properties"
        assert "model_key" in schema["properties"], "Missing model_key property"
        
        print(f"  ✅ schema.json valid ({len(schema['properties'])} properties)")
        return True
    except Exception as e:
        print(f"  ❌ Schema validation failed: {e}")
        return False

def main():
    print("Phase 0 CI Tests (CPU-only)")
    print("=" * 60)
    print()
    
    tests = [
        ("Script imports", test_imports),
        ("Results schema", test_schema),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} raised exception: {e}")
            results.append((name, False))
        print()
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    if all_passed:
        print()
        print("✅ All CI tests passed (GPU tests require RTX 5090)")
        return 0
    else:
        print()
        print("❌ Some CI tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
