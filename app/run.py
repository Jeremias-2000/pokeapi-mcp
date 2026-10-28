import sys
from pathlib import Path

import uvicorn


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    project_root = app_dir.parent
    # app/mcp would otherwise shadow the installed `mcp` SDK package
    sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != app_dir]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.mcp.application.configuration.settings import get_settings
    from app.mcp.infra.logging import LOGGING_CONF

    settings = get_settings()
    uvicorn.run(
        "app.mcp.infra.entrypoints.mcp_server:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=settings.mcp_reload,
        log_config=str(LOGGING_CONF),
    )


if __name__ == "__main__":
    main()
