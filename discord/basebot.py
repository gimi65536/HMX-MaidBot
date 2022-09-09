import discord
from load_db import db
from load_maids import maids, maids_dict
from debug_utils import gen_gids
from server_state import state
from utils import check_server_text_channel

bot = discord.Bot()

@bot.event
async def on_ready():
	print(f'Successfully logged in as Bot {bot.user}.')

# Basic commands

kwargs_for_text_channel = {'checks': [check_server_text_channel], 'guild_ids': gen_gids()}

# After fetch, the state "installed_hooks" should match the maid lists.
# That is, if we have maid A B C, then hooks are like [42, 84, 1].
async def _fetch_maids(ctx, force = False):
	channel = ctx.channel
	channel_id = ctx.channel_id

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

@bot.slash_command(**kwargs_for_text_channel)
async def initialize(ctx):
	await _fetch_maids(ctx)

@bot.slash_command(**kwargs_for_text_channel)
async def update(ctx):
	await _fetch_maids(ctx)

@bot.slash_command(**kwargs_for_text_channel)
async def introduce(ctx):
	await _fetch_maids(ctx)
	...

__all__ = ['bot']