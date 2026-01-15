"""
Aura Logging Module
Tüm logları merkezi olarak yönetir
"""

import logging
import logging.handlers
from pathlib import Path
from config import config
from datetime import datetime

# Log dizini oluştur
LOG_DIR = config.LOG_DIR

class LoggerSetup:
    """Logging sistem kurulum"""
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Belirli bir modül için logger oluştur"""
        
        logger = logging.getLogger(name)
        
        # Eğer zaten handler varsa, tekrar ekleme
        if logger.handlers:
            return logger
        
        # Log seviyesi
        log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
        logger.setLevel(log_level)
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File Handler (Rotating)
        log_file = LOG_DIR / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger


# Module loggers
logger = LoggerSetup.get_logger(__name__)
backend_logger = LoggerSetup.get_logger("backend")
frontend_logger = LoggerSetup.get_logger("frontend")
api_logger = LoggerSetup.get_logger("api")
db_logger = LoggerSetup.get_logger("database")
ml_logger = LoggerSetup.get_logger("ml")
