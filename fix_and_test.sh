#!/bin/bash

# Complete fix and test script for draw system
# Run this on the server after uploading updated code

echo "============================================================"
echo "MILLANCE REWARDS - DRAW SYSTEM FIX & TEST"
echo "============================================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "Step 1: Checking current enum values..."
echo "------------------------------------------------------------"
python check_enum.py
echo ""

read -p "Do you want to fix the enum if values are missing? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Step 2: Fixing enum values..."
    echo "------------------------------------------------------------"
    python fix_enum.py
    echo ""
fi

echo "Step 3: Checking draw eligibility..."
echo "------------------------------------------------------------"
python check_draw_eligibility.py
echo ""

echo "Step 4: Testing API response..."
echo "------------------------------------------------------------"
python test_api_response.py
echo ""

echo "============================================================"
echo "FIX & TEST COMPLETED"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. If all checks passed, go to franchise dashboard"
echo "2. Navigate to 'Draws' tab"
echo "3. Click 'Conduct Draw'"
echo "4. Winner should be selected successfully!"
echo ""
