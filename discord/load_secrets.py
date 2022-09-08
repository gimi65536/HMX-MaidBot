import json

# load secret information
with open('secret.json') as f:
	secret = json.load(f)

__all__ = ['secret']