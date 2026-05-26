import argparse

from src.migrations import migrate
from src.core.config import settings


def _dsn() -> str:
    if settings.MIGRATIONS_DATABASE_URL:
        return settings.MIGRATIONS_DATABASE_URL
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DB migrations from ./src/migrations/sql")
    parser.add_argument("command", choices=["up", "down", "drop"])
    args = parser.parse_args()

    dsn = _dsn()
    if args.command == "up":
        migrate.up(dsn)
    elif args.command == "down":
        migrate.down(dsn)
    else:
        migrate.drop(dsn)


if __name__ == "__main__":
    main()
