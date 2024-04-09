#!/bin/bash

# Directory containing the .xlsx files
DIRECTORY=$1

# Loop over all .xlsx files in the directory
for file in "$DIRECTORY"/*.xlsx; do
    # Extract the base name of the file (without the directory path)
    basename=$(basename "$file")
    
    # Extract the part of the name before the first "_"
    newname="${basename%%_*}.xlsx"
    
    # Get the full path of the new name
    newpath="$DIRECTORY/$newname"
    
    # Rename the file
    mv "$file" "$newpath"
done

echo "Renaming completed."
