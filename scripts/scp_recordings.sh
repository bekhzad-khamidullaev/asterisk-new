#!/bin/bash

# Source server details
source_server="source_server_ip"
source_user="your_username"
source_path="/path/to/source/files"

# Destination server details
destination_server="destination_server_ip"
destination_user="your_username"
destination_path="/path/to/destination/folder"

# Iterate over files in the source directory and copy them to the destination server
for file in "$source_path"/*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        scp "$file" "$destination_user"@"$destination_server":"$destination_path"/"$filename"
        
        if [ $? -eq 0 ]; then
            echo "File $filename copied successfully"
        else
            echo "Error copying file $filename"
        fi
    fi
done
