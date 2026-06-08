import uvicorn
import os
import sys


def main():
    os.environ.setdefault("PYTHONPATH", os.path.dirname(os.path.abspath(__file__)))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
