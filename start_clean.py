#!/usr/bin/env python3
"""
Clean startup script for RAG Search System
Suppresses verbose logging and shows only essential information
"""
import os
import sys
import warnings
from pathlib import Path

# Suppress warnings and verbose outputs
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Set environment variables for clean startup
os.environ["LOG_LEVEL"] = "ERROR"  # Only show errors
os.environ["FLASK_ENV"] = "production"

def main():
    print("🚀 RAG Search System")
    print("=" * 50)
    
    try:
        # Import app after setting environment
        from app import app, initialize_services
        
        # Initialize services
        print("🔧 Initializing services...")
        
        if not initialize_services():
            print("❌ Failed to initialize services")
            sys.exit(1)
        
        print("\n🎉 System ready!")
        print("📍 Access your search system at: http://localhost:5001")
        print("⚡ Health monitoring running in background")
        print("\n⏹️  Press Ctrl+C to stop\n")
        
        # Start Flask app
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=True,  # Disable debug mode for clean output
            use_reloader=False  # Disable reloader to prevent double startup
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down RAG Search System...")
        print("✅ Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting system: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 