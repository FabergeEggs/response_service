import logging
import sys
from src.core.config import settings

def setup_logging():
    """Настройка логгирования для всего приложения"""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    # Уменьшаем шум от некоторых библиотек
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logging.getLogger("response_service")