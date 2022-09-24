import discord
from rollgames import BaseRollGame
from ...utils import send_as

class DiscordRollGame(BaseRollGame):
	def __init__(self, ctx, webhook, initial_text = None, send_options = {}):
		self.ctx = ctx
		self.webhook = webhook
		self.initial = initial_text
		self.options = send_options

	async def _send(self, content):
		if self.initial is not None:
			content = f'{self.initial}\n{content}'
		await send_as(self.ctx, self.webhook, content, **self.options)