#!/usr/bin/env python3
"""
test_table_complete.py — Comprehensive table implementation test
=================================================================

This script validates:
1. Table summaries are loaded correctly
2. Table parts are normalized
3. Table type classification works
4. Prompt builder handles tables correctly
5. All imports work as expected
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_table_summaries():
    """Test table_summaries.py"""
    print("\n" + "="*70)
    print("TEST 1: Table Summaries Module")
    print("="*70)
    
    from table_summaries import TABLE_SUMMARIES, _DEFAULT_TABLE_SUMMARY
    
    # Check all required table types exist
    required_types = [
        "Dining Table", "Coffee Table", "Work Table", 
        "Conference Table", "Side Table", "Generic Table"
    ]
    
    for table_type in required_types:
        assert table_type in TABLE_SUMMARIES, f"Missing {table_type}"
        summary = TABLE_SUMMARIES[table_type]
        assert "character" in summary, f"{table_type} missing 'character'"
        assert "ergonomic_benchmarks" in summary, f"{table_type} missing 'ergonomic_benchmarks'"
        assert "construction" in summary, f"{table_type} missing 'construction'"
        print(f"  ✓ {table_type:<20} - Valid structure")
    
    # Test fallback
    assert _DEFAULT_TABLE_SUMMARY == TABLE_SUMMARIES["Generic Table"]
    print(f"  ✓ Default fallback   - Points to Generic Table")
    
    # Check benchmark keys for Dining Table
    dining = TABLE_SUMMARIES["Dining Table"]
    benchmarks = dining["ergonomic_benchmarks"]
    required_benchmarks = ["TH", "TL", "TW", "LH", "LS", "CW"]
    for key in required_benchmarks:
        assert key in benchmarks, f"Dining Table missing benchmark {key}"
    print(f"  ✓ Dining Table       - Has all benchmarks: {', '.join(required_benchmarks)}")
    
    return True

def test_table_classification():
    """Test table_classification.py"""
    print("\n" + "="*70)
    print("TEST 2: Table Classification Module")
    print("="*70)
    
    from table_classification import normalize_table_parts, classify_table, build_table_prompt_context
    
    # Test 1: normalize_table_parts
    test_cases = [
        (["table_top", "leg", "apron"], {"table_top", "leg", "apron"}),
        (["TABLE_TOP", "Leg", "APRON"], {"table_top", "leg", "apron"}),
        (["tabletop", "legs", "skirt"], {"table_top", "leg", "apron"}),
        (["top", "support", "trim"], {"table_top", "leg", "apron"}),
        ([], set()),
    ]
    
    for inputs, expected in test_cases:
        result = normalize_table_parts(inputs)
        assert result == expected, f"normalize_table_parts({inputs}) = {result}, expected {expected}"
        print(f"  ✓ normalize_table_parts({inputs[:2]}) → {sorted(result)}")
    
    # Test 2: classify_table
    classification_tests = [
        ({"table_top", "leg", "apron"}, "Dining Table"),
        ({"table_top", "pedestal"}, "Coffee Table"),
        ({"table_top", "leg", "apron", "stretcher"}, "Work Table"),
        ({"table_top", "pedestal"}, "Coffee Table"),
        ({"table_top"}, "Generic Table"),
        (set(), "Generic Table"),
    ]
    
    for parts, expected_type in classification_tests:
        table_type, confidence = classify_table(parts)
        assert table_type == expected_type, f"classify_table({parts}) = {table_type}, expected {expected_type}"
        print(f"  ✓ classify_table({sorted(parts)[:2]}...) → {table_type} ({confidence})")
    
    # Test 3: build_table_prompt_context
    context = build_table_prompt_context("Dining Table", {}, {"table_top", "leg", "apron"})
    assert context["table_type"] == "Dining Table"
    assert len(context["focus_areas"]) > 0
    assert len(context["guidance"]) > 0
    print(f"  ✓ build_table_prompt_context - Generates {len(context['focus_areas'])} focus areas")
    
    return True

def test_prompt_builder_integration():
    """Test prompt_builder.py with tables"""
    print("\n" + "="*70)
    print("TEST 3: Prompt Builder Integration")
    print("="*70)
    
    from prompt_builder import TABLE_SUMMARIES as IMPORTED_TABLES, _format_ocr_benchmark_audit
    
    # Check TABLE_SUMMARIES is imported
    assert len(IMPORTED_TABLES) == 6
    assert "Dining Table" in IMPORTED_TABLES
    print(f"  ✓ TABLE_SUMMARIES imported - Contains {len(IMPORTED_TABLES)} table types")
    
    # Test _format_ocr_benchmark_audit with table
    test_measurements = {
        "TH": {"value": 750, "unit": "mm"},
        "TL": {"value": 1500, "unit": "mm"},
        "TW": {"value": 900, "unit": "mm"},
    }
    
    audit = _format_ocr_benchmark_audit(test_measurements, "Dining Table", furniture_type="table")
    assert "TH" in audit, "Audit missing TH"
    assert "OK" in audit or "WARNING" in audit or "CRITICAL" in audit, "Audit missing status"
    assert "table" not in audit or "chair" not in audit.lower(), "Should use 'table' in error messages"
    print(f"  ✓ _format_ocr_benchmark_audit - Generates table-specific audit")
    print(f"    (Sample output: {audit[:100]}...)")
    
    return True

def test_main_integration():
    """Test main.py with table imports"""
    print("\n" + "="*70)
    print("TEST 4: Main Module Integration")
    print("="*70)
    
    import ast
    
    main_file = os.path.join(os.path.dirname(__file__), "main.py")
    with open(main_file, 'r') as f:
        main_content = f.read()
    
    # Check required imports are present
    required_imports = [
        "from table_classification import",
        "normalize_table_parts",
        "classify_table",
        "build_table_prompt_context",
    ]
    
    for required in required_imports:
        assert required in main_content, f"main.py missing: {required}"
        print(f"  ✓ main.py contains: {required}")
    
    # Check normalize_table_parts is used
    assert "normalize_table_parts(detections)" in main_content
    print(f"  ✓ main.py calls normalize_table_parts()")
    
    # Check classify_table is used
    assert "classify_table(parts_set)" in main_content
    print(f"  ✓ main.py calls classify_table()")
    
    return True

def test_frontend_integration():
    """Test Dashboard.jsx with table colors"""
    print("\n" + "="*70)
    print("TEST 5: Frontend Integration")
    print("="*70)
    
    dashboard_file = os.path.join(
        os.path.dirname(__file__), 
        "../frontend/src/pages/Dashboard.jsx"
    )
    
    with open(dashboard_file, 'r') as f:
        dashboard_content = f.read()
    
    # Check table colors in RC
    table_colors = ["top:", "leg:", "apron:", "pedestal:", "stretcher:"]
    for color in table_colors:
        assert color in dashboard_content, f"Dashboard.jsx missing RC.{color}"
        print(f"  ✓ RC dict has: {color}")
    
    # Check table part mappings in RM
    table_mappings = ["table_top:", "leg:", "apron:", "pedestal:", "stretcher:"]
    for mapping in table_mappings:
        assert mapping in dashboard_content, f"Dashboard.jsx missing RM.{mapping}"
        print(f"  ✓ RM dict has: {mapping}")
    
    # Check furniture_type selector
    assert 'furniture_type' in dashboard_content
    assert '"table"' in dashboard_content or "'table'" in dashboard_content
    print(f"  ✓ Dashboard has furniture_type selector")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "█"*70)
    print("█  DesignableAI Table Implementation - Comprehensive Test Suite")
    print("█"*70)
    
    tests = [
        ("Table Summaries", test_table_summaries),
        ("Table Classification", test_table_classification),
        ("Prompt Builder Integration", test_prompt_builder_integration),
        ("Main Module Integration", test_main_integration),
        ("Frontend Integration", test_frontend_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            if test_func():
                results.append((test_name, "PASS"))
                print(f"\n✅ {test_name}: PASSED")
        except AssertionError as e:
            results.append((test_name, f"FAIL: {e}"))
            print(f"\n❌ {test_name}: FAILED")
            print(f"   Error: {e}")
            return False
        except Exception as e:
            results.append((test_name, f"ERROR: {e}"))
            print(f"\n❌ {test_name}: ERROR")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Summary
    print("\n" + "█"*70)
    print("█  TEST SUMMARY")
    print("█"*70)
    for test_name, result in results:
        status = "✅" if result == "PASS" else "❌"
        print(f"{status} {test_name:<35} {result}")
    
    print("\n" + "█"*70)
    all_passed = all(r == "PASS" for _, r in results)
    if all_passed:
        print("✅ ALL TESTS PASSED! Table implementation is complete.")
    else:
        print("❌ Some tests failed. Please review above.")
    print("█"*70 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
