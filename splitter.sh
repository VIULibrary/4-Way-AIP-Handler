#!/bin/bash

# ===== EDIT THESE VALUES =====
SOURCE_FOLDER="/Volumes/Vintage-1/2024-04-05to2025-10-31"
CSV_FILE="2024-04-05to2025-10-31.csv"
BASE_NAME="2024-04-05to2025-10-31"
NUM_SPLITS=2  # > for more splits
OUTPUT_PATH="/path/to/output"  # (use "." for current directory)
# =============================

echo "=========================================="
echo "Starting split archive process..."
echo "Source: $SOURCE_FOLDER"
echo "CSV file: $CSV_FILE"
echo "Number of splits: $NUM_SPLITS"
echo "Output path: $OUTPUT_PATH"
echo "=========================================="

# Verify the path exists
if [ ! -d "$OUTPUT_PATH" ]; then
    echo "Error: Directory '$OUTPUT_PATH' does not exist."
    exit 1
fi

# Generate suffix letters (A, B, C, D, etc.)
SUFFIXES=()
for i in $(seq 0 $((NUM_SPLITS - 1))); do
    SUFFIXES+=("$(printf "\\$(printf '%03o' $((65 + i)))")")
done

# Create temp dirs
echo ""
echo "Creating temporary directories..."
for SUFFIX in "${SUFFIXES[@]}"; do
    mkdir -p "${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}"
    echo "  Created ${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}/"
done

# Copy CSV to all folders
echo ""
echo "Copying CSV to all archives..."
for SUFFIX in "${SUFFIXES[@]}"; do
    cp "${SOURCE_FOLDER}/${CSV_FILE}" "${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}/"
    echo "  ✓ Copied to ${BASE_NAME}-${SUFFIX}/"
done

# Get all files except the CSV, sorted by size (largest first)
echo ""
echo "Analyzing files..."
FILES=($(find "$SOURCE_FOLDER" -maxdepth 1 -type f ! -name "$CSV_FILE" -exec stat -f "%z %N" {} + | sort -rn | awk '{print $2}'))
TOTAL_FILES=${#FILES[@]}
echo "Found $TOTAL_FILES files to distribute (excluding CSV)"

# Initialize size and count arrays
declare -a SIZES
declare -a COUNTS
for i in $(seq 0 $((NUM_SPLITS - 1))); do
    SIZES[$i]=0
    COUNTS[$i]=0
done

# Distribute files by size to balance the archives
echo ""
echo "Distributing files..."
CURRENT=0

for FILE in "${FILES[@]}"; do
    CURRENT=$((CURRENT + 1))
    FILE_SIZE=$(stat -f "%z" "$FILE")
    FILENAME=$(basename "$FILE")
    
    # Find the archive with the smallest current size
    MIN_IDX=0
    MIN_SIZE=${SIZES[0]}
    for i in $(seq 1 $((NUM_SPLITS - 1))); do
        if [ ${SIZES[$i]} -lt $MIN_SIZE ]; then
            MIN_SIZE=${SIZES[$i]}
            MIN_IDX=$i
        fi
    done
    
    # Copy to the archive with smallest size
    SUFFIX=${SUFFIXES[$MIN_IDX]}
    cp "$FILE" "${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}/"
    SIZES[$MIN_IDX]=$((${SIZES[$MIN_IDX]} + FILE_SIZE))
    COUNTS[$MIN_IDX]=$((${COUNTS[$MIN_IDX]} + 1))
    
    echo "[$CURRENT/$TOTAL_FILES] → ${SUFFIX}: $FILENAME ($(echo "scale=2; $FILE_SIZE/1048576" | bc) MB)"
done

echo ""
echo "=========================================="
echo "Distribution complete:"
for i in $(seq 0 $((NUM_SPLITS - 1))); do
    SUFFIX=${SUFFIXES[$i]}
    echo "  Archive ${SUFFIX}: ${COUNTS[$i]} files ($(echo "scale=2; ${SIZES[$i]}/1048576" | bc) MB)"
done
echo "=========================================="

# Ask user if they want to zip
echo ""
read -p "Do you want to create 7z archives? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create the 7z archives
    echo ""
    for SUFFIX in "${SUFFIXES[@]}"; do
        echo "Creating ${BASE_NAME}-${SUFFIX}.7z..."
        cd "$OUTPUT_PATH"
        7z a "${BASE_NAME}-${SUFFIX}.7z" "${BASE_NAME}-${SUFFIX}"
        cd - > /dev/null
        echo ""
    done

    # Clean up temp dirs
    echo "Cleaning up temporary directories..."
    for SUFFIX in "${SUFFIXES[@]}"; do
        rm -rf "${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}"
    done

    echo ""
    echo "=========================================="
    echo "✓ Complete!"
    for i in $(seq 0 $((NUM_SPLITS - 1))); do
        SUFFIX=${SUFFIXES[$i]}
        echo "Created ${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}.7z (${COUNTS[$i]} files + CSV)"
    done
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "✓ Folders created but not zipped"
    echo "Folders are ready at:"
    for SUFFIX in "${SUFFIXES[@]}"; do
        echo "  ${OUTPUT_PATH}/${BASE_NAME}-${SUFFIX}/"
    done
    echo "=========================================="
fi