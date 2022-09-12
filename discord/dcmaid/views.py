import discord

class _Button(discord.ui.Button):
	def __init__(self, callback, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._c = callback

	async def callback(self, interaction: discord.Interaction):
		await self._c(self, interaction)

async def _default_yes_callback(button, interaction):
	# no-op
	pass

async def _default_no_callback(button, interaction):
	await interaction.delete_original_message()

class YesNoView(discord.ui.View):
	def __init__(self,
		yes_label = 'Yes',
		no_label = 'No',
		yes_style = discord.ButtonStyle.primary,
		no_style = discord.ButtonStyle.secondary,
		yes_emoji = None,
		no_emoji = None,
		yes_callback = _default_yes_callback,
		no_callback = _default_no_callback,
		yes_left = True,
		**kwargs
	):
		super().__init__(**kwargs)
		self._yes = _Button(callback = yes_callback, label = yes_label, style = yes_style, emoji = yes_emoji)
		self._no = _Button(callback = no_callback, label = no_label, style = no_style, emoji = no_emoji)

		if yes_left:
			self.add_item(self._yes)
			self.add_item(self._no)
		else:
			self.add_item(self._no)
			self.add_item(self._yes)

		self._yc = yes_callback
		self._nc = no_callback
