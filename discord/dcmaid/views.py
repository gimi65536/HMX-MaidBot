from __future__ import annotations
import discord
from collections.abc import Coroutine
from typing import Any, Callable, Optional, TypeAlias

class Button(discord.ui.Button):
	def __init__(self, callback: ButtonCallback, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._c = callback

	async def callback(self, interaction: discord.Interaction):
		await self._c(self, interaction)

ButtonCallback: TypeAlias = Callable[[Button, discord.Interaction], Coroutine[Any, Any, Any]]

class Select(discord.ui.Select):
	def __init__(self, callback: SelectCallback, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._c = callback

	async def callback(self, interaction: discord.Interaction):
		await self._c(self, interaction)

SelectCallback: TypeAlias = Callable[[Select, discord.Interaction], Coroutine[Any, Any, Any]]

async def _default_yes_callback(button: Button, interaction: discord.Interaction):
	await interaction.response.edit_message(content = "Yes", view = None)

async def _default_no_callback(button: Button, interaction: discord.Interaction):
	await interaction.response.edit_message(content = "No", view = None)

class YesNoView(discord.ui.View):
	def __init__(self,
		yes_label: str = 'Yes',
		no_label: str = 'No',
		yes_style: discord.ButtonStyle = discord.ButtonStyle.primary,
		no_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
		yes_emoji: Optional[discord.PartialEmoji | discord.Emoji | str] = None,
		no_emoji: Optional[discord.PartialEmoji | discord.Emoji | str] = None,
		yes_callback: ButtonCallback = _default_yes_callback,
		no_callback: ButtonCallback = _default_no_callback,
		yes_left: bool = True,
		**kwargs
	):
		super().__init__(**kwargs)
		self._yes = Button(callback = yes_callback, label = yes_label, style = yes_style, emoji = yes_emoji)
		self._no = Button(callback = no_callback, label = no_label, style = no_style, emoji = no_emoji)

		if yes_left:
			self.add_item(self._yes)
			self.add_item(self._no)
		else:
			self.add_item(self._no)
			self.add_item(self._yes)
