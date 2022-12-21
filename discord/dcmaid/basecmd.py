import discord
import discord.utils
import re
from collections.abc import Mapping
from functools import partial
from types import MappingProxyType
from typing import Optional
from .basebot import Bot
from .basecog import BaseCog
from .exception import MaidNotFound
from .helper import get_help, set_help
from .perm import admin_only
from .utils import *
from .views import YesNoView
from .weight import Weight

# This cog (name = 'Base') defines the basic commands.
class BasicCommands(BaseCog, name = 'Base', elementary = True):
	def __init__(self, bot: Bot):
		super().__init__(bot)

	system = discord.SlashCommandGroup(
		name = "system",
		description = "Bot system settings",
		guild_only = True
	)
	set_help(system,
		'''
		These commands are related to core settings of maids and {bot}.
		Can be only called in a server channel.
		'''
	)

	# After fetch, the state "installed_hooks" should match the maid mapping.
	# Also, note that we don't store webhook tokens in our db but store the
	# full webhooks (containing tokens) in the server state.
	async def _fetch_maids(self, channel, force = False) -> Mapping[str, discord.Webhook]:
		channel_id = channel.id

		col = self.db['channel-installed-maids']

		# Here, we use "hook" to indicate the webhooks we know from our db,
		# and "webhook" to the real webhooks in the channel.
		installed_hooks: Optional[Mapping[str, discord.Webhook]] = self.state.get_installed_hooks(channel_id)

		if force or installed_hooks is None:
			installed_hooks_dict: dict[str, discord.Webhook] = {}

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
			installed_hooks = MappingProxyType({maid_name: installed_hooks_dict[maid_name] for maid_name in self.maids.keys()})
			self.state.set_installed_hooks(channel_id, installed_hooks)

		return installed_hooks

	async def fetch_maids(self, channel: discord.abc.GuildChannel):
		'''
		This method should be called in every command if the command uses maids.
		An extension will call this method with `bot.get_cog('Base').fetch_maids(channel)`.
		'''
		return await self._fetch_maids(channel)

	@system.command(
		description = 'Initialize or update the maids'
	)
	async def initialize(self, ctx):
		'''
		`/{cmd_name}` is a basic command that users can call first to add maids (webhooks).
		This command will not do anything if the server process already has the information \
		of the channel, so this command is free to call by any user.
		This command is not really needed to call as each command with maids ought to call \
		the fetch method first.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await self.fetch_maids(get_guild_channel(ctx.channel))
		await ctx.send_response(
			content = self._trans(ctx, 'succ-init'),
			ephemeral = True
		)

	@system.command(
		description = 'Force the channel to synchronize the maids information',
		default_member_permissions = admin_only
	)
	async def update(self, ctx):
		'''
		`/{cmd_name}` lets server OPs force to fetch the maid information stored on the process.
		Usually users need this command if some maids are fired/deleted...
		This command is for OPs only.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await self._fetch_maids(ctx, True)
		await ctx.send_response(
			content = self._trans(ctx, 'succ-update'),
			ephemeral = True
		)

	async def _uninstall(self, ctx, button, interaction):
		await interaction.response.defer()
		await interaction.edit_original_message(content = self._trans(ctx, 'uninstalling'), view = None)

		await self._fetch_maids(ctx, True)

		channel_id = ctx.channel_id
		webhooks = self.state.get_installed_hooks(channel_id)

		for webhook in webhooks.values():
			await webhook.delete()

		self.db['channel-installed-maids'].delete_many({'channel_id': channel_id})
		self.state.remove_installed_hooks(channel_id)

		await interaction.edit_original_message(
			content = self._trans(ctx, 'succ-uninst')
		)

	@system.command(
		description = 'Uninstall maids',
		default_member_permissions = admin_only
	)
	async def uninstall(self, ctx):
		'''
		`/{cmd_name}` will delete the webhooks installed in this channel.
		This command will fetch the maids information first.
		This command is for OPs only.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await ctx.send_response(
			content = self._trans(ctx, 'ensure-uninst'),
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

	maid_setting = system.create_subgroup(
		name = 'weight',
		description = 'About the weight of appearances of the bot and the maids'
	)
	set_help(maid_setting,
		'''
		Some commands are designed to respond as a character chosen randomly, \
		and these setting commands are here to manipulate the weight of appearances (in this channel) \
		of {bot} and the maids.
		Note that by default, the weight is 1 to all characters.
		Also, DM channels does not have maids (webhooks) and those commands \
		using maids only responds as {bot} herself.
		Can be only called in a server channel.
		'''
	)

	def fetch_weight(self, channel: discord.abc.GuildChannel):
		return Weight(self.bot, channel)

	@maid_setting.command(
		name = 'get',
		description = 'Get the weight of appearances of the maids.',
		options = [
			discord.Option(str,
				name = 'maid',
				description = 'Choose maid (Optional)',
				autocomplete = autocomplete_get_maid_names,
				default = '')
		]
	)
	async def weight_get(self, ctx, maid_name: str):
		'''
		`/{cmd_name} <?maid name>` returns the weight of appearances of a maid in this channel.
		If maid is not given, returns the appearance weights of all the maids and {bot}.
		Can be only called in a server channel.
		'''
		maid_name = trim(maid_name)
		if maid_name != '' and maid_name not in self.maids:
			raise MaidNotFound(maid_name)

		w = self.fetch_weight(get_guild_channel(ctx.channel))
		embed = discord.Embed(title = self._trans(ctx, 'weight'), color = discord.Color.blue())
		if maid_name == '':
			# All character
			embed.add_field(
				name = self._trans(ctx, 'myself', format = {'bot': get_bot_name_in_ctx(ctx)}),
				value = str(w.get_bot_weight()),
				inline = True
			)
			for maid in self.maids:
				embed.add_field(name = maid, value = str(w.get_maid_weight(maid)), inline = True)
		else:
			embed.add_field(name = maid_name, value = str(w.get_maid_weight(maid_name)), inline = True)

		await ctx.send_response(embed = embed)

	@maid_setting.command(
		name = 'get-bot',
		description = 'Get the weight of appearances of the bot.'
	)
	async def weight_get_bot(self, ctx):
		'''
		`/{cmd_name}` returns the weight of appearances of {bot} in this channel.
		Can be only called in a server channel.
		'''
		w = self.fetch_weight(get_guild_channel(ctx.channel))
		embed = discord.Embed(title = self._trans(ctx, 'weight'), color = discord.Color.blue())
		embed.add_field(
			name = self._trans(ctx, 'myself', format = {'bot': get_bot_name_in_ctx(ctx)}),
			value = str(w.get_bot_weight()),
			inline = True
		)

		await ctx.send_response(embed = embed)

	@maid_setting.command(
		name = 'set',
		description = 'Set the weight of appearances of the maids.',
		options = [
			discord.Option(str,
				name = 'maid',
				description = 'Choose maid',
				autocomplete = autocomplete_get_maid_names),
			discord.Option(int,
				name = 'weight',
				description = 'Input the weight of appearances (a non-negative integer)',
				min_value = 0)
		]
	)
	async def weight_set(self, ctx, maid_name, weight):
		'''
		`/{cmd_name} <maid name> <weight>` sets the weight of appearances of a maid in this channel.
		Can be only called in a server channel.
		'''
		maid_name = trim(maid_name)
		if maid_name not in self.maids:
			raise MaidNotFound(maid_name)

		w = self.fetch_weight(get_guild_channel(ctx.channel))
		w.set_maid_weight(maid_name, weight)

		embed = discord.Embed(title = self._trans(ctx, 'weight-set'), color = discord.Color.green())
		embed.add_field(name = self._trans(ctx, 'succ-weight-set'),
			value = self._trans(ctx, 'succ-weight-set-value', format = {'name': maid_name, 'weight': weight})
		)

		await ctx.send_response(embed = embed)

	@maid_setting.command(
		name = 'set-bot',
		description = 'Set the weight of appearances of the bot.',
		options = [
			discord.Option(int,
				name = 'weight',
				description = 'Input the weight of appearances (a non-negative integer)',
				min_value = 0)
		]
	)
	async def weight_set_bot(self, ctx, weight):
		'''
		`/{cmd_name} <weight>` sets the weight of appearances of {bot} in this channel.
		Can be only called in a server channel.
		'''
		w = self.fetch_weight(get_guild_channel(ctx.channel))
		w.set_bot_weight(weight)

		embed = discord.Embed(title = self._trans(ctx, 'weight-set'), color = discord.Color.green())
		embed.add_field(name = self._trans(ctx, 'succ-weight-set'),
			value = self._trans(ctx, 'succ-weight-set-bot-value', format = {'bot': get_bot_name_in_ctx(ctx), 'weight': weight})
		)

		await ctx.send_response(embed = embed)

	@discord.slash_command(
		description = 'Introduce the maids',
		guild_only = True,
		options = [
			discord.Option(str,
				name = 'maid',
				description = 'What maid to introduce? (Optional)',
				autocomplete = autocomplete_get_maid_names,
				default = None)
		]
	)
	async def introduce(self, ctx, maid_name):
		'''
		`/{cmd_name} <?maid name>` is a basic command to let {bot} introduce maids we have.
		This command also attempt to add maids if the server process has not remembered the \
		channel, just like what the initialize command does, so this command is free to call by any user.
		Can be only called in a server channel.
		'''
		await self.fetch_maids(get_guild_channel(ctx.channel))

		maid_name = trim(maid_name)

		if maid_name is None or maid_name not in self.maids:
			# Introduce all maids
			await ctx.send_response("Here puts introduce.")
		else:
			if maid_name not in self.maids:
				NotImplemented
			# Introduce a specific maid
			await ctx.send_response(f"Here puts introduce of {maid_name}.")

	@discord.slash_command(
		description = 'Retrieve the server time'
	)
	async def now(self, ctx):
		'''
		`/{cmd_name}` returns the server time.
		'''
		embed = discord.Embed(title = discord.Embed.Empty, color = discord.Color.blue())
		embed.add_field(name = self._trans(ctx, 'current-time'), value = discord.utils.format_dt(discord.utils.utcnow()), inline = False)
		embed.set_footer(text = self._trans(ctx, 'shown-timezone'))
		await ctx.send_response(embed = embed)

	async def _cls(self, button, interaction):
		await interaction.response.defer()
		await interaction.edit_original_message(content = self._trans(interaction, 'deleting'), view = None)

		channel = interaction.channel

		if (is_not_DM(channel) and hasattr(channel, 'purge')) or isinstance(channel, discord.Thread):
			# TextChannel, VoiceChannel, ForumChannel, and Thread
			await channel.purge(limit = None, reason = 'Clear all messages in the channel') # type: ignore
		elif is_DM(channel):
			messages = []
			async for m in channel.history(limit = None):
				if m.author == self.bot.user:
					messages.append(m)
			for m in messages:
				await m.delete()
		else:
			raise discord.InvalidArgument('Unknown channel type')

	@discord.slash_command(
		description = 'Clear the chat room',
		default_member_permissions = discord.Permissions(manage_messages = True)
	)
	async def cls(self, ctx):
		'''
		`/{cmd_name}` will clear the chat room.
		If it is called in DM channels, only the messages sent by {bot} get deleted.
		This command is for channel managers only.
		The response of the command is ephemeral.
		'''
		await ctx.send_response(
			content = self._trans(ctx, 'ensure-delete'),
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

	@discord.slash_command(
		description = 'Get illustration of a command',
		options = [
			discord.Option(str,
				name = 'command',
				description = 'What command to illustrate (Optional)',
				default = 'help')
		]
	)
	async def help(self, ctx, cmd_name):
		'''
		`/{cmd_name}` <?command name> gives the illustration of the command written by the author.
		Internally, this command retrieves `__commands_help__` of every command as illustration \
		by default, or the description will be returned.
		'''
		cmd_name = trim(cmd_name)
		if not cmd_name:
			# None, '', etc.
			cmd_name = 'help'

		cmd_name = re.sub(r'\s+', ' ', cmd_name)
		cmd_names = cmd_name.split()
		fail = False
		if len(cmd_names) > 0 and (main_cmd := self.bot.get_application_command(cmd_names.pop(0), type = discord.ApplicationCommand)) is not None:
			parent_cmd = main_cmd
			for n in cmd_names:
				if isinstance(parent_cmd, discord.SlashCommand) or not isinstance(parent_cmd, discord.SlashCommandGroup):
					# No subcommand
					fail = True
					break

				# parent is a group
				cmd = get_subcommand(parent_cmd, n)
				if cmd is None:
					fail = True
					break

				parent_cmd = cmd

			if not fail:
				cmd = parent_cmd
			else:
				cmd = None
		else:
			fail = True
			cmd = None

		if fail:
			await send_error_embed(ctx,
				name = self._trans(ctx, 'help-no-cmd'),
				value = self._trans(ctx, 'help-no-cmd-value', format = {'cmd_name': cmd_name})
			)
		else:
			assert isinstance(cmd, discord.SlashCommand)
			doc_locale_table = get_help(cmd)
			locale = ctx.locale
			if locale not in doc_locale_table:
				doc = doc_locale_table.get(None, None)
			else:
				doc = doc_locale_table[locale]

			if doc is None: # Caused by get(None, None)
				doc_locale_table = cmd.description_localizations
				if doc_locale_table is not None and locale in doc_locale_table:
					doc = doc_locale_table[locale]
				else:
					doc = cmd.description # There SHOULD be a string, not None

			embed = discord.Embed(color = discord.Color.green(), title = self._trans(ctx, 'Help'))
			embed.add_field(
				name = f'/{cmd_name}',
				value = doc.format(cog = self, bot = get_bot_name_in_ctx(ctx), cmd_name = cmd_name)
			)
			await ctx.send_response(embed = embed)

	class _SpeakModal(discord.ui.Modal):
		# Add outer to enable localization of the cog. Maybe it is awful.
		def __init__(self, outer, locale, webhook = None, *args, **kwargs):
			super().__init__(title = outer._trans(locale, 'speak-modal-title'), *args, **kwargs)
			self._trans = outer._trans
			self.locale = locale
			self.webhook = webhook

			self.add_item(discord.ui.InputText(label = self._trans(locale, 'speak-modal-label'), style = discord.InputTextStyle.long))

		async def callback(self, interaction):
			value = self.children[0].value
			if value is None:
				value = ''

			text = value.strip()
			if len(text) == 0:
				await send_error_embed(interaction,
					name = self._trans(self.locale, 'speak-modal-empty'),
					value = self._trans(self.locale, 'speak-modal-empty-value'),
					ephemeral = True
				)
				return

			await interaction.response.defer()
			await send_as(interaction, self.webhook, text)

	@discord.slash_command(
		description = 'Send a message as the bot or a maid',
		default_member_permissions = admin_only,
		guild_only = True,
		options = [
			discord.Option(str,
				name = 'maid',
				description = 'What maid? (Empty to use the bot)',
				autocomplete = autocomplete_get_maid_names,
				default = ''
			),
			discord.Option(str,
				name = 'text',
				description = 'What to say? (Empty to call a modal)',
				default = ''
			)
		]
	)
	async def speak(self, ctx, maid_name, text):
		'''
		`/{cmd_name}` <?maid_name> <?text> is a command to make a maid send a message.
		If the name is not provided, then {bot} herself will speak the text.
		If the text is not provided, then a form is given to type a long article
		(up to 1024 characters).
		This command is for OPs only.
		Can be only called in a server channel.
		'''
		await self.fetch_maids(get_guild_channel(ctx.channel))

		maid_name = trim(maid_name)
		if maid_name != '' and maid_name not in self.maids:
			raise MaidNotFound(maid_name)

		webhook = self.state.get_installed_hooks(ctx.channel_id).get(maid_name, None)

		if len(text) == 0:
			await ctx.send_modal(self._SpeakModal(self, ctx.locale, webhook))
		else:
			await remove_thinking(ctx)
			await send_as(ctx, webhook, text)

__all__ = ['BasicCommands']

def setup(bot):
	bot.add_cog(BasicCommands(bot))
