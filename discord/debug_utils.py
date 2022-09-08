from load_secrets import secret

def gen_gids():
	if __debug__:
		return [secret['debug_server_id']]
	return None