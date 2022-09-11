from decouple import config

secret = {
	"app_id": config('APP_ID', cast = int),
	"app_client_secret": config('APP_CLIENT_SECRET'),
	"bot_token": config('BOT_TOKEN'),
	"mongo_address": config('MONGO_ADDRESS'),
	"mongo_admin": config('MONGO_ADMIN'),
	"mongo_pwd": config('MONGO_PWD'),
	"debug_server_id": config('DEBUG_SERVER_ID', cast = int)
}

__all__ = ['secret']