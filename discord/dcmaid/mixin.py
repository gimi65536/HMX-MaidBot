import discord
import random
from collections.abc import Mapping
from typing import cast, Optional
from .basebot import Bot
from .basecmd import BasicCommands
from .state import State
from .typing import Channelable, QuasiContext
from .utils import *
from .weight import Weight

class MaidMixin:
	bot: Bot

	# You need to override cog_before_invoke manually when inherit the mixin
	async def _cog_before_invoke(self, ctx):
		if is_DM(ctx.channel):
			return

		base_cog = self.bot.get_cog('Base')
		assert isinstance(base_cog, BasicCommands)
		maid_webhook = await base_cog.fetch_maids(get_guild_channel(ctx.channel))
		maid_weights = base_cog.fetch_weight(get_guild_channel(ctx.channel))
		setattr(ctx, 'maid_webhook', maid_webhook)
		setattr(ctx, 'maid_weights', maid_weights)

	async def _get_webhook_by_name(self, ctx: Channelable, maid_name):
		if ctx.channel is not None and is_not_DM(ctx.channel):
			if hasattr(ctx, 'maid_webhook'):
				maid_webhook = cast(Mapping[str, discord.Webhook], getattr(ctx, 'maid_webhook'))
			else:
				base_cog = self.bot.get_cog('Base')
				assert isinstance(base_cog, BasicCommands)
				maid_webhook = await base_cog.fetch_maids(get_guild_channel(ctx.channel))

			webhook = maid_webhook.get(maid_name, None)
		else:
			webhook = None

		return webhook

	# Since webhooks cannot really reply or followup messages as a bot,
	# here we simulate those with plain messages whoever the sender is.
	async def _send_followup(self, ctx: QuasiContext, maid, *args, **kwargs):
		webhook = await self._get_webhook_by_name(ctx, maid)
		await send_as(ctx, webhook, *args, **kwargs)

	def _random_maid(self, ctx: Channelable):
		# If RandomMixin is not installed, Weight will use the built-in random generator.
		if ctx.channel is not None and is_not_DM(ctx.channel):
			maid = None
			maid_weights = None

			# The negative case of typeguard does not narrow types (PEP 647)
			assert not isinstance(ctx.channel, discord.PartialMessageable | discord.abc.PrivateChannel)

			if hasattr(ctx, 'maid_weights'):
				maid_weights = cast(Weight, getattr(ctx, 'maid_weights'))
			else:
				base_cog = self.bot.get_cog('Base')
				assert isinstance(base_cog, BasicCommands)
				maid_weights = base_cog.fetch_weight(get_guild_channel(ctx.channel))

			if isinstance(self, RandomMixin):
				maid = maid_weights.random_get(self._get_random_generator(ctx))
			else:
				maid = maid_weights.random_get()

			return maid
		else:
			return None

class RandomMixin:
	state: State
	__state_random_key__ = 'random_generator_{}'

	def _get_random_generator(self, ctx: Channelable) -> random.Random:
		channel = ctx.channel

		if channel is not None and is_not_DM(channel):
			channel = get_guild_channel(channel)
			generator = cast(random.Random, self.state.get(self.__state_random_key__.format(channel.id)))
			if generator is None:
				generator = random.Random()
				self.state.set(self.__state_random_key__.format(channel.id), generator)
		else:
			if not hasattr(self, '_common_random'):
				generator = random.Random()
				setattr(self, '_common_random', generator) # Used in DM
			else:
				generator = cast(random.Random, getattr(self, '_common_random'))

		return generator

	def _set_seed(self, ctx: Channelable, seed: Optional[str]):
		if ctx.channel is not None and is_not_DM(ctx.channel):
			channel = get_guild_channel(ctx.channel)
			generator = random.Random(seed)
			self.state.set(self.__state_random_key__.format(channel.id), generator)
