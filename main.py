# main.py
import uvicorn
import argparse
from src import config_loader as config
from webapp.app_main import app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FastAPI app")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to run the app on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the app on")
    args = parser.parse_args()

    config.set_config("./webapp/web_config.yaml")
    uvicorn.run(app, host=args.host, port=args.port)
