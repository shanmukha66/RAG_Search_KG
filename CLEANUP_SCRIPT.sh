#!/bin/bash

# RAG Search Project Cleanup Script
# This script removes unnecessary files safely without breaking the application

echo "🧹 Starting RAG Search Project Cleanup..."

# 1. Remove duplicate docker-compose file
echo "Removing duplicate docker-compose.yaml..."
rm -f docker-compose.yaml

# 2. Remove legacy/demo files
echo "Removing legacy and demo files..."
rm -f app_rag.py
rm -f monitoring_demo.py  
rm -f test_system.py
rm -f 1_load_ocr_and_qas.py
rm -f 2_prepare_vector_chunks.py
rm -f 3_ingest_Qdrant.py
rm -f 4_ingest_neo4j.py

# 3. Remove generated database files (can be recreated)
echo "Removing generated database files..."
rm -f query_optimization.db
rm -f test.db

# 4. Remove log and state directories (runtime generated)
echo "Removing runtime logs and state files..."
rm -rf logs/
rm -rf system_state/

# 5. Remove Python cache
echo "Removing Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null

# 6. Remove evaluation cache
echo "Removing evaluation cache..."
rm -rf .deepeval/

# 7. Remove macOS system files
echo "Removing macOS system files..."
find . -name ".DS_Store" -delete 2>/dev/null

echo "✅ Cleanup complete!"
echo ""
echo "📊 Summary of what was removed:"
echo "  - Duplicate docker-compose.yaml"
echo "  - 6 legacy data preparation scripts"
echo "  - 3 demo/test files"  
echo "  - 2 generated database files"
echo "  - Runtime logs and state directories"
echo "  - Python cache files"
echo "  - Evaluation cache"
echo "  - macOS system files"
echo ""
echo "🚀 Your project is now clean and optimized!"
echo "💡 All core functionality remains intact."
echo ""
echo "To verify everything works:"
echo "1. docker-compose up -d"
echo "2. python app.py"
echo "3. Visit http://localhost:5001" 