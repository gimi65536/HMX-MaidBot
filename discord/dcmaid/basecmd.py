import discord
from functools import partial
from types import MappingProxyType
from typing import Dict, Tuple
from .basebot import Bot
from .helper import get_help
from .utils import *
from .views import YesNoView

perm_admin_only = discord.Permissions(administrator = True)

# This cog (name = 'Base') defines the basic commands.
class BasicCommands(discord.Cog, name = 'Base'):
	# Notice that we only accept the bot of '.basebot.Bot' class or its subclasses.
	def __init__(self, bot: Bot):
		if not isinstance(bot, Bot):
			raise TypeError('Only accepts basebot.Bot type.')

		self.bot = bot
		self.db = bot.db
		self.maids = bot.maids
		self.state = bot.state

	# After fetch, the state "installed_hooks" should match the maid mapping.
	# Also, note that we don't store webhook tokens in our db but store the
	# full webhooks (containing tokens) in the server state.
	async def _fetch_maids(self, ctx, force = False):
		channel = get_guild_channel(ctx.channel)
		channel_id = ctx.channel_id

		col = self.db['channel-installed-maids']

		# Here, we use "hook" to indicate the webhooks we know from our db,
		# and "webhook" to the real webhooks in the channel.
		installed_hooks = self.state.get_installed_hooks(channel_id)

		if force or installed_hooks is None:
			installed_hooks_dict: Dict[str, discord.Webhook] = {}

			# If the state already stores the information, we don't start a
			# query again. We trust users not to delete the webhooks (maids).
			channel_webhooks = await channel.webhooks()
			channel_webhooks_dict = {h.id: h for h in channel_webhooks}
			channel_webhooks_id = set(h.id for h in channel_webhooks)
			registered_hooks = list(col.find({'channel_id': channel_id}))
			registered_hooks_id = set(h['hook_id'] for h in registered_hooks)

			# 1. Check if some hooks are deleted
			for h_id in (registered_hooks_id - channel_webhooks_id):
				col.delete_one({'channel_id': channel_id, 'hook_id': h_id})

			# Now, these are in the new version. All registered hooks corresponds an active webhook.
			# The query operation is supposed to be cheap because we index 'channel_id' and 'hook_id' columns
			registered_hooks = list(col.find({'channel_id': channel_id}))
			registered_hooks_id = set(h['hook_id'] for h in registered_hooks)

			undealt_maids = set(self.maids.keys())
			# 2. Check if some registered maids are removed from our DB and update to new information if any
			for hook in registered_hooks:
				maid_name = hook['name']
				h_id = hook['hook_id']
				webhook = channel_webhooks_dict[h_id]
				if maid_name not in undealt_maids:
					# This maid may be fired by us, or the channel has redundant maids (how can this happen?)
					await webhook.delete()
					col.delete_one({'channel_id': channel_id, 'hook_id': h_id})
				else:
					# Update maids information
					maid = self.maids[maid_name]
					undealt_maids.remove(maid_name)
					await webhook.edit(reason = 'Fetch maid information', name = maid.display_name, avatar = maid.avatar)
					installed_hooks_dict[maid_name] = webhook

			# 3. Add new cute maids!
			for maid_name in undealt_maids:
				maid = self.maids[maid_name]
				webhook = await channel.create_webhook(reason = 'Add new maid', name = maid.display_name, avatar = maid.avatar)
				col.insert_one({'channel_id': channel_id, 'name': maid_name, 'hook_id': webhook.id})
				installed_hooks_dict[maid_name] = webhook

			# Reorder the installed_hooks to match the maids order
			installed_hooks: Mapping[str, discord.Webhook] = \
				MappingProxyType({maid_name: installed_hooks_dict[maid_name] for maid_name in self.maids.keys()})
			self.state.set_installed_hooks(channel_id, installed_hooks)

	async def fetch_maids(self, ctx):
		'''
		This method should be called in every command if the command uses maids.
		An extension will call this method with `bot.get_cog('Base').fetch_maids(ctx)`.
		'''
		await self._fetch_maids(ctx)

	@discord.commands.slash_command(
		description = 'Initialize or update the maids',
		guild_only = True
	)
	async def initialize(self, ctx):
		'''
		`/initialize` is a basic command that users can call first to add maids (webhooks).
		This command will not do anything if the server process already has the information
		of the channel, so this command is free to call by any user.
		This command is not really needed to call as each command with maids ought to call
		the fetch method first.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await self.fetch_maids(ctx)
		await ctx.send_response(
			content = "Successfully Initialized.",
			ephemeral = True
		)

	@discord.commands.slash_command(
		description = 'Force the channel to synchronize the maids information',
		default_member_permissions = perm_admin_only,
		guild_only = True
	)
	async def update(self, ctx):
		'''
		`/update` lets server OPs force to fetch the maid information stored on the process.
		This command is for OPs only.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await self._fetch_maids(ctx, True)
		await ctx.send_response(
			content = "Successfully Updated.",
			ephemeral = True
		)

	async def _uninstall(self, ctx, button, interaction):
		await interaction.response.defer()
		await interaction.edit_original_message(content = "Uninstalling...", view = None)

		await self._fetch_maids(ctx, True)

		channel = get_guild_channel(ctx.channel)
		channel_id = ctx.channel_id
		webhooks = self.state.get_installed_hooks(channel_id)

		for webhook in webhooks.values():
			await webhook.delete()

		self.db['channel-installed-maids'].delete_many({'channel_id': channel_id})
		self.state.remove_installed_hooks(channel_id)

		await interaction.edit_original_message(
			content = "Successfully Uninstalled."
		)

	@discord.commands.slash_command(
		description = 'Uninstall maids',
		default_member_permissions = perm_admin_only,
		guild_only = True
	)
	async def uninstall(self, ctx):
		'''
		`/uninstall` will delete the webhooks installed in this channel.
		This command will fetch the maids information first.
		This command is for OPs only.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await ctx.send_response(
			content = "Are you sure to uninstall? (Press `Yes` in 3 minutes)",
			ephemeral = True,
			view = YesNoView(
				yes_label = 'Yes',
				no_label = 'No',
				yes_style = discord.ButtonStyle.danger,
				no_style = discord.ButtonStyle.secondary,
				yes_callback = partial(self._uninstall, ctx),
				yes_left = True,
				timeout = 180.0
			),
			delete_after = 180.0
		)

	@discord.commands.slash_command(
		description = 'Introduce the maids',
		guild_only = True,
		options = [
			discord.Option(
				name = 'maid',
				description = 'What maid to introduce? (Optional)',
				input_type = str,
				autocomplete = autocomplete_get_maid_names,
				default = None)
		]
	)
	async def introduce(self, ctx, maid_name):
		'''
		`/introduce` is a basic command to let the bot introduce maids we have.
		This command also attempt to add maids if the server process has not remembered the
		channel, just like what `/initialize` does, so this command is free to call by any user.
		Can be only called in a server channel.
		'''
		await self.fetch_maids(ctx)

		maid_name = trim(maid_name)

		if maid_name is None or maid_name not in self.maids:
			# Introduce all maids
			await ctx.send_response("Here puts introduce.")
		else:
			if maid_name not in self.maids:
				NotImplemented
			# Introduce a specific maid
			await ctx.send_response(f"Here puts introduce of {maid_name}.")

	@discord.commands.slash_command(
		description = 'Retrieve the server time'
	)
	async def now(self, ctx):
		'''
		`/now` returns the server time.
		'''
		t = int(discord.utils.utcnow().timestamp())
		embed = discord.Embed(title = discord.Embed.Empty, color = discord.Color.blue())
		embed.add_field(name = "Current Time", value = f"<t:{t}:f>", inline = False)
		embed.set_footer(text = "Shown in your timezone")
		await ctx.send_response(embed = embed)

	async def _cls(self, button, interaction):
		await interaction.response.defer()
		await interaction.edit_original_message(content = "Deleting...", view = None)

		channel = interaction.channel

		if (isinstance(channel, discord.abc.GuildChannel) and hasattr(channel, 'purge')) or isinstance(channel, discord.Thread):
			# TextChannel, VoiceChannel, ForumChannel, and Thread
			await channel.purge(limit = None, reason = 'Clear all messages in the channel')
		elif isinstance(channel, discord.PartialMessageable) or isinstance(channel, discord.DMChannel):
			# So far, the DMChannel case won't be triggered at all.
			messages = []
			async for m in channel.history(limit = None):
				if m.author == self.bot.user:
					messages.append(m)
			for m in messages:
				await m.delete()
		else:
			raise discord.InvalidArgument('Unknown channel type')

	@discord.commands.slash_command(
		description = 'Clear the chat room',
		default_member_permissions = discord.Permissions(manage_messages = True)
	)
	async def cls(self, ctx):
		'''
		`/cls` will clear the chat room.
		If it is called in DM channels, only the messages sent by the bot get deleted.
		This command is for channel managers only.
		The response of the command is ephemeral.
		'''
		await ctx.send_response(
			content = "Are you sure to delete all messages? (Press `Yes` in 3 minutes)",
			ephemeral = True,
			view = YesNoView(
				yes_label = 'Yes',
				no_label = 'No',
				yes_style = discord.ButtonStyle.danger,
				no_style = discord.ButtonStyle.secondary,
				yes_callback = self._cls,
				yes_left = True,
				timeout = 180.0
			),
			delete_after = 180.0
		)

	@discord.commands.slash_command(
		description = 'Get illustration of a command',
		options = [
			discord.Option(
				name = 'command',
				description = 'What command to illustrate',
				input_type = str,
				default = 'help')
		]
	)
	async def help(self, ctx, cmd_name):
		'''
		`/help` <command name> gives the illustration of the command written by the author.
		Internally, this command retrieves `__commands_help__` of every command as illustration.
		by default, or the description will be returned.
		'''
		cmd_name = trim(cmd_name)
		if not cmd_name:
			# None, '', etc.
			cmd_name = 'help'

		cmd = self.bot.get_application_command(cmd_name)
		if cmd is None:
			await send_error_embed(ctx,
				name = 'Command not found',
				value = f'`/{cmd_name}` is not found! Please check the command name.'
			)
		else:
			doc = get_help(cmd)
			if doc is None:
				try:
					doc = cmd.description
				except:
					# When the command does not support description...
					doc = '**No illustration found.**'
			embed = discord.Embed(color = discord.Color.green(), title = 'Help')
			embed.add_field(
				name = f'/{cmd_name}',
				value = doc.format(cog = self, bot = self.bot)
			)
			await ctx.send_response(embed = embed)

	class _SpeakModal(discord.ui.Modal):
		def __init__(self, webhook = None, *args, **kwargs):
			super().__init__(title = "Input text", *args, **kwargs)
			self.webhook = webhook

			self.add_item(discord.ui.InputText(label = 'Input', style = discord.InputTextStyle.long))

		async def callback(self, interaction):
			text = self.children[0].value
			if len(text) == 0:
				await send_error_embed(interaction,
					name = 'Empty Content',
					value = f'The text cannot be empty.',
					ephemeral = True
				)
				return

			await interaction.response.defer()
			channel = interaction.channel

			if self.webhook is None:
				# Use bot
				await channel.send(text)
			else:
				# Use webhook
				if isinstance(interaction.channel, discord.Thread):
					await self.webhook.send(text, thread = channel)
				else:
					await self.webhook.send(text)

	@discord.commands.slash_command(
		description = 'Send a message as the bot or a maid',
		default_member_permissions = perm_admin_only,
		guild_only = True,
		options = [
			discord.Option(
				name = 'maid',
				description = 'What maid?',
				input_type = str,
				autocomplete = autocomplete_get_maid_names,
				default = ''
			),
			discord.Option(
				name = 'text',
				description = 'What to say? (Empty to call a modal)',
				input_type = str,
				default = ''
			)
		]
	)
	async def speak(self, ctx, maid_name, text):
		'''
		`/speak` <maid_name> is a command to make a maid send a message.
		This command is for OPs only.
		Can be only called in a server channel.
		'''
		await self.fetch_maids(ctx)

		maid_name = trim(maid_name)
		if maid_name != '' and maid_name not in self.maids:
			await send_error_embed(ctx,
				name = 'Maid not found',
				value = f'`/{maid_name}` is not found! Please check the maid name.',
				ephemeral = True
			)
		else:
			if maid_name == '':
				if len(text) == 0:
					await ctx.send_modal(self._SpeakModal())
				else:
					await remove_thinking(ctx)
					await ctx.channel.send(text)
			else:
				installed_hooks = self.state.get_installed_hooks(ctx.channel_id)
				webhook = installed_hooks[maid_name]
				if len(text) == 0:
					await ctx.send_modal(self._SpeakModal(webhook))
				else:
					await remove_thinking(ctx)
					if isinstance(ctx.channel, discord.Thread):
						await webhook.send(text, thread = ctx.channel)
					else:
						await webhook.send(text)

__all__ = ['BasicCommands']

def setup(bot):
	bot.add_cog(BasicCommands(bot))
