import discord
from load_db import db
from load_maids import maids, maids_dict
from debug_utils import gen_gids
from server_state import state

bot = discord.Bot()

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

# Basic commands

kwargs_for_text_channel = {'guild_only': True, 'guild_ids': gen_gids()}
perm_admin_only = discord.Permissions(administrator = True)

# After fetch, the state "installed_hooks" should match the maid lists.
# That is, if we have maid A B C, then hooks are like [42, 84, 1].
async def _fetch_maids(ctx, force = False):
	channel = ctx.channel
	channel_id = ctx.channel_id

	# Here, we use "hook" to indicate the webhooks we know from our db,
	# and "webhook" to the real webhooks in the channel.
	installed_hooks = state.get_installed_hooks(channel_id)

	if force or installed_hooks is None:
		installed_hooks_dict = {}

		# If the state already stores the information, we don't start a
		# query again. We trust users not to delete the webhooks (maids).
		channel_webhooks = await channel.webhooks()
		channel_webhooks_dict = {h.id: h for h in channel_webhooks}
		channel_webhooks_id = set(h.id for h in channel_webhooks)
		registered_hooks = list(db['channel-installed-maids'].find({'channel_id': channel_id}))
		registered_hooks_id = set(h['hook_id'] for h in registered_hooks)

		# 1. Check if some hooks are deleted
		for h_id in (registered_hooks_id - channel_webhooks_id):
			db.delete_one({'channel_id': channel_id, 'hook_id': h_id})

		# Now, these are in the new version. All registered hooks corresponds an active webhook.
		# The query operation is supposed to be cheap because we index 'channel_id' and 'hook_id' columns
		registered_hooks = list(db['channel-installed-maids'].find({'channel_id': channel_id}))
		registered_hooks_id = set(h['hook_id'] for h in registered_hooks)

		undealt_maids = set(maids_dict.keys())
		# 2. Check if some registered maids are removed from our DB and update to new information if any
		for hook in registered_hooks:
			maid_name = hook['name']
			h_id = hook['hook_id']
			webhook = channel_webhooks_dict[h_id]
			if maid_name not in undealt_maids:
				# This maid may be fired by us, or the channel has redundant maids (how can this happen?)
				await webhook.delete()
				db.delete_one({'channel_id': channel_id, 'hook_id': h_id})
			else:
				# Update maids information
				maid = maids_dict[maid_name]
				undealt_maids.remove(maid_name)
				await webhook.edit(reason = 'Fetch maid information', name = maid.display_name, avatar = maid.avatar_base64)
				installed_hooks_dict[maid_name] = webhook.id

		# 3. Add new cute maids!
		for maid_name in undealt_maids:
			maid = maids_dict[maid_name]
			webhook = await channel.create_webhook(reason = 'Add new maid', name = maid.display_name, avatar = maid.avatar_base64)
			db.insert_one({'channel_id': channel_id, 'name': maid_name, 'hook_id': webhook.id})
			installed_hooks_dict[maid_name] = webhook.id

		# Reorder the installed_hooks to match the maids order
		installed_hooks = tuple(installed_hooks_dict[maid_name] for maid_name in maids_dict.keys())
		state.set_installed_hooks(channel_id, installed_hooks)

@bot.slash_command(
	description = 'Initialize or update the maids',
	**kwargs_for_text_channel
)
async def initialize(ctx):
	'''
	/initialize is a basic command that users should call first to add maids (webhooks).
	This command will not do anything if the server process already has the information
	of the channel, so this command is free to call by any user.
	The response of the command is ephemeral.
	'''
	await _fetch_maids(ctx)
	await ctx.send_response(
		content = "Successfully Initialized.",
		ephemeral = True
	)

@bot.slash_command(
	description = 'Force the channel to synchronize the maids information',
	default_member_permissions = perm_admin_only,
	**kwargs_for_text_channel
)
async def update(ctx):
	'''
	/update lets server OPs force to fetch the maid information stored on the process.
	This command is for OPs only.
	The response of the command is ephemeral.
	'''
	await _fetch_maids(ctx, True)
	await ctx.send_response(
		content = "Successfully Updated.",
		ephemeral = True
	)

@bot.slash_command(
	description = 'Introduce the maids',
	**kwargs_for_text_channel
)
async def introduce(ctx):
	'''
	/introduce is a basic command to let the bot introduce maids we have.
	This command also attempt to add maids if the server process has not remembered the
	channel, just like what /initialize does, so this command is free to call by any user.
	'''
	await _fetch_maids(ctx)
	await ctx.send_response("Here puts introduce.")

__all__ = ['bot']