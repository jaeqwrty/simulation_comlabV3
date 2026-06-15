"""Launch the ComLab V3 Python simulation app via FastAPI."""

import argparse
import webbrowser
import uvicorn
import threading
import time

def open_browser(url: str):
    time.sleep(1.5)
    webbrowser.open(url)

def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Run the ComLab V3 FastAPI simulation app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="Start the server without opening a browser tab.")
    args = parser.parse_args(argv)

    url = f"http://{args.host}:{args.port}"
    print(f"ComLab V3 FastAPI server running at {url}")
    
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run("comlab_v3.web:app", host=args.host, port=args.port, reload=True)

if __name__ == "__main__":
    main()
