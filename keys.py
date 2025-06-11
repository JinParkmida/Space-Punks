from typing import Optional, List
from dotenv import load_dotenv
from os import getenv
from util import logger


def make_int(var):
    if not var:
        return None
    try:
        return int(var)
    except Exception as exc:
        logger.warn(
            f"{exc} (Exception) -> Failed to turn {var} of type {type(var)} into an integer. -> module.keys.make_int"
        )
        return None


def make_list(var: str, make_integer=False):
    if not var:
        return []
    split_list = var.split(",")
    if make_integer:
        return [make_int(val) for val in split_list]
    return split_list


class Keys:
    def __init__(self):
        # Bot Info
        self.prod_bot_token: str = ""
        self.dev_bot_token: str = ""
        self.bot_id: int = 0
        self.bot_owner_id: int = 0
        self.bot_name: str = ""
        self.bot_prefix: str = ""

        # Database Server (PostgreSQL)
        self.db_host: str = ""
        self.db_name: str = ""
        self.db_user: str = ""
        self.db_pass: str = ""
        self.db_port: int = 0

        # Support Server
        self.support_server_id: int = 0
        self.bot_owner_only_servers: List[int] = []

        self.refresh_env()

    def get_keys(self, *args) -> dict:
        """Return list of key arguments as a dictionary."""
        keys = dict()
        for arg in args:
            keys[arg] = self.__dict__[arg]
        return keys

    def refresh_env(self):
        """Update the values in the .env file."""
        load_dotenv()
        self.__define_keys()

    def __define_keys(self):
        keys = dict(
            {
                # Bot Info
                "prod_bot_token": getenv("PROD_BOT_TOKEN"),
                "dev_bot_token": getenv("DEV_BOT_TOKEN"),
                "bot_id": make_int(getenv("BOT_ID")),
                "bot_owner_id": make_int(getenv("BOT_OWNER_ID")),
                "bot_name": getenv("BOT_NAME"),
                "bot_prefix": getenv("BOT_DEFAULT_PREFIX"),
                
                # Database Server
                "db_host": getenv("DB_HOST"),
                "db_name": getenv("DB_NAME"),
                "db_user": getenv("DB_USER"),
                "db_pass": getenv("DB_PASS"),
                "db_port": make_int(getenv("PRT_DB")),
                
                # Support Server
                "support_server_id": make_int(getenv("SUPPORT_SERVER_ID")),
                "bot_owner_only_servers": make_list(
                    getenv("BOT_OWNER_ONLY_SERVERS"), make_integer=True
                ),
            }
        )

        for key, val in keys.items():
            if val is not None and type(self.__getattribute__(key)) != type(val):
                logger.warn(
                    f"Environment variable {key} has type {type(val)}"
                    f" when type {type(self.__getattribute__(key))} was expected."
                )
            self.__setattr__(key, val)

        no_vals = [key for key, value in keys.items() if not value]
        logger.warn(
            f"Could not find an environment value for keys: {', '.join(no_vals)}."
        )


_keys: Optional[Keys] = None


def get_keys():
    global _keys
    if not _keys:
        _keys = Keys()
    return _keys