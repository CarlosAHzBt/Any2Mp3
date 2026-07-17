"""Ventana de escritorio de Any2Mp3."""

import webview

from app import create_app


def main() -> None:
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window(
        "Any2Mp3",
        create_app(),
        width=1180,
        height=820,
        min_size=(900, 650),
        background_color="#0f172a",
    )
    webview.start()


if __name__ == "__main__":
    main()
