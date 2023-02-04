from decouple import config, Csv
from typing import TypedDict

class _Secret(TypedDict):
	app_id: int
	app_client_secret: str
	bot_token: str
	mongo_address: str
	mongo_admin: str
	mongo_pwd: str
	mongo_db: str
	debug_server_id: list[int]
	load_ext: list[str]

secret: _Secret = { # type: ignore # python-decouple doesn't provide typing
	"app_id": config('APP_ID', cast = int),
	"app_client_secret": config('APP_CLIENT_SECRET'),
	"bot_token": config('BOT_TOKEN'),
	"mongo_address": config('MONGO_ADDRESS'),
	"mongo_admin": config('MONGO_ADMIN'),
	"mongo_pwd": config('MONGO_PWD'),
	"mongo_db": config('MONGO_DB'),
	"debug_server_id": config('DEBUG_SERVER_ID', cast = Csv(int)),
	"load_ext": config('LOAD_EXT', default = '', cast = Csv())
}

__all__ = ['secret']