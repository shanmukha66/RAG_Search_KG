#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting cleanup of large data files...${NC}"

# Function to safely remove files
safe_remove() {
    if [ -f "$1" ]; then
        size=$(du -h "$1" | cut -f1)
        echo -e "${YELLOW}Found $1 (Size: $size)${NC}"
        read -p "Do you want to remove this file? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$1"
            echo -e "${GREEN}Removed $1${NC}"
        else
            echo -e "${YELLOW}Skipping $1${NC}"
        fi
    fi
}

# Function to safely remove backup files
remove_backups() {
    if [ -f "$1" ]; then
        size=$(du -h "$1" | cut -f1)
        echo -e "${YELLOW}Found backup file $1 (Size: $size)${NC}"
        rm "$1"
        echo -e "${GREEN}Removed backup file $1${NC}"
    fi
}

# Check and remove main data files
echo -e "\n${YELLOW}Checking for main data files...${NC}"
safe_remove "ocr_data.json"
safe_remove "qa_data.json"
safe_remove "vector_chunks.json"

# Remove backup files without asking
echo -e "\n${YELLOW}Cleaning up backup files...${NC}"
remove_backups "ocr_data.json.bak"
remove_backups "qa_data.json.bak"
remove_backups "vector_chunks.json.bak"

# Remove temporary files without asking
echo -e "\n${YELLOW}Cleaning up temporary files...${NC}"
find . -name "*.json.tmp" -type f -delete
find . -name "*.tmp" -type f -delete

# Clean up processed data
echo -e "\n${YELLOW}Checking processed data directory...${NC}"
if [ -d "processed_data" ]; then
    size=$(du -sh processed_data | cut -f1)
    echo -e "${YELLOW}Found processed_data directory (Size: $size)${NC}"
    read -p "Do you want to remove the processed_data directory? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf processed_data
        echo -e "${GREEN}Removed processed_data directory${NC}"
    else
        echo -e "${YELLOW}Skipping processed_data directory${NC}"
    fi
fi

# Clean up ingestion logs
echo -e "\n${YELLOW}Cleaning up ingestion logs...${NC}"
if [ -d "ingestion_logs" ]; then
    rm -rf ingestion_logs
    echo -e "${GREEN}Removed ingestion logs${NC}"
fi

echo -e "\n${GREEN}Cleanup complete!${NC}"

# Git status check
echo -e "\n${YELLOW}Checking git status...${NC}"
if command -v git &> /dev/null && [ -d .git ]; then
    git status
    echo -e "\n${YELLOW}If any large files are still tracked by git, you can untrack them with:${NC}"
    echo "git rm --cached <filename>"
    echo "git commit -m 'Remove large files from git tracking'"
fi 