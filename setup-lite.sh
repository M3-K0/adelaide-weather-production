#!/bin/bash
# Adelaide Weather - Lite Setup Script
# Generates test indices and data for local development

set -e

echo "=========================================="
echo "Adelaide Weather - Lite Setup"
echo "=========================================="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

echo "📦 Installing Python dependencies..."
pip install -q numpy pandas faiss-cpu pyarrow 2>/dev/null || {
    echo "⚠️  Warning: Failed to install some dependencies"
    echo "   This might be because they're already installed"
}

echo ""
echo "🔨 Creating test FAISS indices and embeddings..."
python3 create_test_indices.py

echo ""
echo "📁 Creating outcomes directory..."
mkdir -p outcomes
mkdir -p models

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Generated directories:"
echo "   - indices/     (FAISS index files)"
echo "   - embeddings/  (embedding vectors and metadata)"
echo "   - outcomes/    (empty, ready for use)"
echo "   - models/      (empty, ready for use)"
echo ""
echo "🚀 You can now run:"
echo "   docker-compose -f docker-compose.lite.yml up -d"
echo ""
