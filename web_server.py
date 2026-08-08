#!/usr/bin/env python3
"""
MeetSpot Local Development Server
=================================

This is the main entry point for local development.
It imports and runs the FastAPI application from api/index.py.

For production deployment on Railway, this file serves as the main entry point.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def main():
    """Main entry point for development and production server"""
    try:
        # Import the FastAPI app from api/index.py
        from api.index import app  # noqa: F401
        import uvicorn
        
        # Get port from environment variable (Railway sets PORT automatically)
        port = int(os.environ.get("PORT", 8000))
        
        # Detect if running in production (Railway sets RAILWAY_ENVIRONMENT)
        is_production = os.environ.get("RAILWAY_ENVIRONMENT") is not None
        
        if is_production:
            print("🚀 启动 MeetSpot 生产服务器 (Railway)...")
            print(f"📍 服务端口: {port}")
        else:
            print("🚀 启动 MeetSpot 本地开发服务器...")
            print(f"📍 服务地址: http://localhost:{port}")
        
        print("📚 API文档: /docs")
        print("🔧 健康检查: /health")
        print("=" * 50)
        
        # Run the server with production-optimized settings
        uvicorn.run(
            "api.index:app", 
            host="0.0.0.0", 
            port=port,
            reload=not is_production,  # Disable reload in production
            log_level="info",
            access_log=True
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
