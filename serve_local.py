"""Serve the built site on loopback; JSON loading requires HTTP."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


def main():
    directory = Path(__file__).resolve().parent / "dist"
    if not (directory / "index.html").exists():
        raise SystemExit("請先執行 python build_commercial_html.py")
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 18765), handler)
    except OSError as error:
        raise SystemExit("無法使用本機連接埠 18765，請先關閉舊的本機網站視窗／伺服器後重試。") from error
    with server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"網站已開啟：{url}\n結束使用時按 Ctrl+C。")
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
