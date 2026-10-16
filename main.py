"""ASGI entry point for local Uvicorn and Render deployments."""

if __name__ == "__main__":
    from desktop_gui import App

    desktop_app = App()
    desktop_app.mainloop()
else:
    from app.main import app

    __all__ = ["app"]
