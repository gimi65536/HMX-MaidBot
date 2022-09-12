import discord
from functools import partial
from typing import Dict, Tuple
from .basebot import Bot
from .utils import autocomplete_get_maid_names
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

	# After fetch, the state "installed_hooks" should match the maid lists.
	# That is, if we have maid A B C, then hooks are like [42, 84, 1].
	# Also, note that we don't store webhook tokens in our db but store the
	# full webhooks (containing tokens) in the server state.
	async def _fetch_maids(self, ctx, force = False):
		channel = ctx.channel
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
			installed_hooks: Tuple[discord.Webhook, ...] = tuple(installed_hooks_dict[maid_name] for maid_name in self.maids.keys())
			self.state.set_installed_hooks(channel_id, installed_hooks)

	@discord.commands.slash_command(
		description = 'Initialize or update the maids',
		guild_only = True
	)
	async def initialize(self, ctx):
		'''
		/initialize is a basic command that users should call first to add maids (webhooks).
		This command will not do anything if the server process already has the information
		of the channel, so this command is free to call by any user.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await self._fetch_maids(ctx)
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
		/update lets server OPs force to fetch the maid information stored on the process.
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
		await self._fetch_maids(ctx, True)

		channel = ctx.channel
		channel_id = ctx.channel_id
		webhooks = self.state.get_installed_hooks(channel_id)

		for webhook in webhooks:
			await webhook.delete()

		self.db['channel-installed-maids'].delete_many({'channel_id': channel_id})
		self.state.remove_installed_hooks(channel_id)

		await interaction.response.edit_message(
			content = "Successfully Uninstalled.",
			view = None
		)

	@discord.commands.slash_command(
		description = 'Uninstall maids',
		default_member_permissions = perm_admin_only,
		guild_only = True
	)
	async def uninstall(self, ctx):
		'''
		/uninstall will delete the webhooks installed in this channel.
		This command will fetch the maids information first.
		This command is for OPs only.
		The response of the command is ephemeral.
		Can be only called in a server channel.
		'''
		await ctx.send_response(
			content = "Are you sure to uninstall?",
			ephemeral = True,
			view = YesNoView(
				yes_label = 'Yes',
				no_label = 'No',
				yes_style = discord.ButtonStyle.danger,
				no_style = discord.ButtonStyle.secondary,
				yes_callback = partial(self._uninstall, ctx),
				yes_left = True,
				timeout = 180.0,
				disable_on_timeout = True
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
		/introduce is a basic command to let the bot introduce maids we have.
		This command also attempt to add maids if the server process has not remembered the
		channel, just like what /initialize does, so this command is free to call by any user.
		Can be only called in a server channel.
		'''
		await self._fetch_maids(ctx)
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
		/now returns the server time.
		'''
		t = int(discord.utils.utcnow().timestamp())
		embed = discord.Embed(title = discord.Embed.Empty, color = discord.Color.blue())
		embed.add_field(name = "Current Time", value = f"<t:{t}:f>", inline = False)
		embed.set_footer(text = "Shown in your timezone")
		await ctx.send_response(embed = embed)

__all__ = ['BasicCommands']

def setup(bot):
	bot.add_cog(BasicCommands(bot))
