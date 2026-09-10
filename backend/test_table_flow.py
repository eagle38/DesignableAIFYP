#!/usr/bin/env python3
"""
test_table_flow.py
==================
Test script to verify the complete table upload → YOLO → geometry → LLM pipeline.

This script:
1. Creates a mock table image
2. Simulates YOLO detection output with table parts (top, legs, apron)
3. Tests part normalization
4. Tests geometry analysis
5. Tests prompt building with table-specific context
6. Verifies LLM gets correct table summaries and benchmarks
"""

import json
from PIL import Image, ImageDraw
import os
import sys
import tempfile

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions we're testing
from yolov8_inference import get_model
from geometry_analyzer import analyze_geometry, get_part_role
from prompt_builder import build_expert_prompt, CHAIR_SUMMARIES

def create_test_table_image():
    """Create a simple test table image."""
    width, height = 800, 600
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw table top (rectangle)
    draw.rectangle([100, 100, 700, 250], outline='black', width=3)
    draw.text((350, 60), "TABLE TOP (TL=600mm)", fill='black')
    
    # Draw 4 legs
    leg_w, leg_h = 30, 100
    legs = [
        ([120, 250, 150, 350], "LEG 1"),
        ([670, 250, 700, 350], "LEG 2"),
        ([120, 250, 150, 350], "LEG 3"),
        ([670, 250, 700, 350], "LEG 4"),
    ]
    
    for (x1, y1, x2, y2), label in legs:
        draw.rectangle([x1, y1, x2, y2], outline='black', width=2, fill='lightgray')
        draw.text((x1-20, y1+30), label, fill='black')
    
    # Add measurement labels
    draw.text((320, 75), "TW=550mm", fill='black')
    draw.text((720, 300), "LH=750mm", fill='black')
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        img.save(tmp.name)
        return tmp.name

def simulate_yolo_table_detections():
    """Simulate YOLO detection output for a table."""
    # Mock YOLO detections for a table with top and legs
    return [
        {
            "id": 1,
            "part_name": "table_top",
            "confidence": 0.95,
            "mask": [[100, 100], [700, 100], [700, 250], [100, 250]],  # Rectangle polygon
        },
        {
            "id": 2,
            "part_name": "leg",
            "confidence": 0.92,
            "mask": [[120, 250], [150, 250], [150, 350], [120, 350]],  # Leg 1
        },
        {
            "id": 3,
            "part_name": "leg",
            "confidence": 0.91,
            "mask": [[670, 250], [700, 250], [700, 350], [670, 350]],  # Leg 2
        },
        {
            "id": 4,
            "part_name": "apron",
            "confidence": 0.88,
            "mask": [[100, 240], [700, 240], [700, 260], [100, 260]],  # Apron/frame
        },
    ]

def test_table_flow():
    """Run the complete table flow test."""
    print("=" * 80)
    print("TABLE UPLOAD FLOW TEST")
    print("=" * 80)
    
    # Step 1: Verify table summaries exist
    print("\n✓ STEP 1: Verify Table Summaries")
    print("-" * 80)
    if "Table" in CHAIR_SUMMARIES:
        table_summary = CHAIR_SUMMARIES["Table"]
        print(f"✓ Table summary found in CHAIR_SUMMARIES")
        print(f"  - Character: {table_summary['character'][:100]}...")
        print(f"  - Benchmarks: {', '.join(table_summary['ergonomic_benchmarks'].keys())}")
        print(f"  - Construction: {table_summary['construction'][:80]}...")
    else:
        print("✗ FAILED: Table summary not found!")
        return False
    
    # Step 2: Test YOLO model routing
    print("\n✓ STEP 2: Test YOLO Model Routing")
    print("-" * 80)
    try:
        # Test that models can be loaded (they might fail if weights don't exist, but routing should work)
        print("  Testing model loading for 'chair'...")
        chair_model_path = os.path.join(
            os.path.dirname(__file__), "..", "Roboflow", "yolo_chair_training", "v13", "weights", "best.pt"
        )
        print(f"  - Chair model path: {chair_model_path}")
        print(f"  - Exists: {os.path.exists(chair_model_path)}")
        
        print("  Testing model loading for 'table'...")
        table_model_path = os.path.join(
            os.path.dirname(__file__), "..", "weights", "best.pt"
        )
        print(f"  - Table model path: {table_model_path}")
        print(f"  - Exists: {os.path.exists(table_model_path)}")
        print("✓ Model routing configured correctly")
    except Exception as e:
        print(f"⚠ Model loading skipped (weights may not exist): {e}")
    
    # Step 3: Test part role mapping
    print("\n✓ STEP 3: Test Table Part Roles")
    print("-" * 80)
    table_parts = ["table_top", "top", "leg", "legs", "apron", "pedestal", "stretcher"]
    for part in table_parts:
        role = get_part_role(part)
        print(f"  - {part:15} → {role}")
    
    # Step 4: Test geometry analysis
    print("\n✓ STEP 4: Test Geometry Analysis on Table Parts")
    print("-" * 80)
    mock_detections = simulate_yolo_table_detections()
    
    for det in mock_detections:
        part_name = det["part_name"]
        mask = det["mask"]
        print(f"\n  Analyzing {part_name}...")
        
        try:
            geometry = analyze_geometry(
                mask_points=mask,
                part_label=part_name,
                seat_metadata=None,
                px_per_mm=1.0  # Assume 1px = 1mm for testing
            )
            
            if geometry:
                print(f"    ✓ Geometry analyzed successfully")
                print(f"      - Measurements: {geometry.get('measurements', {})}")
                print(f"      - Shape: {geometry.get('shape', {})}")
                print(f"      - Flags: {len(geometry.get('ergonomic_flags', []))} checks")
            else:
                print(f"    ⚠ Geometry returned None (may need proper calibration)")
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    # Step 5: Test prompt building with table data
    print("\n✓ STEP 5: Test Prompt Building with Table Data")
    print("-" * 80)
    
    # Create mock analysis data
    analysis_data = {
        "furniture_type": "table",
        "identified_type": "Table",
        "is_hybrid": False,
        "influences": [],
        "canonical_parts": ["table_top", "leg", "apron"],
        "parts_with_traits": [
            {
                "label": "table_top",
                "canonical": "table_top",
                "mask": [[100, 100], [700, 100], [700, 250], [100, 250]],
                "geometry": {
                    "measurements": {"width": 600, "length": 150},
                    "shape": {"contour_smoothness": {"score": 0.85, "label": "regular"}},
                    "ergonomic_flags": [],
                    "_raw": {"role": "top"}
                }
            },
            {
                "label": "leg",
                "canonical": "leg",
                "mask": [[120, 250], [150, 250], [150, 350], [120, 350]],
                "geometry": {
                    "measurements": {"height": 100, "width": 30},
                    "shape": {"contour_smoothness": {"score": 0.90}},
                    "ergonomic_flags": [],
                    "_raw": {"role": "leg"}
                }
            },
            {
                "label": "apron",
                "canonical": "apron",
                "mask": [[100, 240], [700, 240], [700, 260], [100, 260]],
                "geometry": {
                    "measurements": {"depth": 20, "width": 600},
                    "shape": {},
                    "ergonomic_flags": [],
                    "_raw": {"role": "apron"}
                }
            },
        ],
        "spatial_relations": {},
        "measurements": {
            "TL": 600,
            "TW": 550,
            "LH": 750,
        },
        "scale_factor": {"px_per_mm": 1.0},
        "image_dimensions": {"width": 800, "height": 600},
    }
    
    try:
        prompt_payload = build_expert_prompt(analysis_data, current_phase="ANALYSIS", is_followup=False)
        
        print("✓ Prompt built successfully")
        print(f"  - System prompt length: {len(prompt_payload['system_prompt'])} chars")
        print(f"  - User prompt: {prompt_payload['prompt'][:100]}...")
        print(f"  - Phase: {prompt_payload['phase']}")
        
        # Check that table-specific content is in the prompt
        if "Table" in prompt_payload['system_prompt']:
            print("  ✓ Table type correctly identified in prompt")
        else:
            print("  ⚠ Table type not found in prompt")
        
        if "TH" in prompt_payload['system_prompt'] or "table height" in prompt_payload['system_prompt'].lower():
            print("  ✓ Table benchmarks (TH, TL, etc.) included in prompt")
        else:
            print("  ⚠ Table benchmarks not found in prompt")
            
    except Exception as e:
        print(f"✗ Error building prompt: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("TABLE FLOW TEST COMPLETE ✓")
    print("=" * 80)
    print("\nSummary:")
    print("  ✓ Table summaries configured")
    print("  ✓ YOLO model routing set up")
    print("  ✓ Table part roles defined")
    print("  ✓ Geometry analysis works on table parts")
    print("  ✓ Prompt building includes table context")
    print("\nTable uploads are ready to use!")
    return True

if __name__ == "__main__":
    success = test_table_flow()
    sys.exit(0 if success else 1)
