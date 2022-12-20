import random
from typing import Optional
from .basebot import Bot
from .basecmd import BasicCommands
from .state import State
from .typing import Channelable, QuasiContext
from .utils import *

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
		if is_DM(ctx.channel):
			webhook = None
		else:
			if hasattr(ctx, 'maid_webhook'):
				maid_webhook = ctx.maid_webhook
			else:
				base_cog = self.bot.get_cog('Base')
				assert isinstance(base_cog, BasicCommands)
				maid_webhook = await base_cog.fetch_maids(get_guild_channel(ctx.channel))

			webhook = maid_webhook.get(maid_name, None)

		return webhook

	# Since webhooks cannot really reply or followup messages as a bot,
	# here we simulate those with plain messages whoever the sender is.
	async def _send_followup(self, ctx: QuasiContext, maid, *args, **kwargs):
		webhook = await self._get_webhook_by_name(ctx, maid)
		await send_as(ctx, webhook, *args, **kwargs)

	def _random_maid(self, ctx: Channelable):
		# If RandomMixin is not installed, Weight will use the built-in random generator.
		maid = None
		maid_weights = None
		if is_DM(ctx.channel):
			return None

		if hasattr(ctx, 'maid_weights'):
			maid_weights = ctx.maid_weights
		else:
			base_cog = self.bot.get_cog('Base')
			assert isinstance(base_cog, BasicCommands)
			maid_weights = base_cog.fetch_weight(get_guild_channel(ctx.channel))

		if isinstance(self, RandomMixin):
			maid = maid_weights.random_get(self._get_random_generator(ctx))
		else:
			maid = maid_weights.random_get()

		return maid

class RandomMixin:
	state: State
	__state_random_key__ = 'random_generator_{}'

	def _get_random_generator(self, ctx: Channelable) -> random.Random:
		channel = ctx.channel
		if is_DM(channel):
			if not hasattr(self, '_common_random'):
				setattr(self, '_common_random', random.Random()) # Used in DM

			return self._common_random  # type: ignore[attr-defined]

		channel = get_guild_channel(channel)
		generator = self.state.get(self.__state_random_key__.format(channel.id))
		if generator is None:
			generator = random.Random()
			self.state.set(self.__state_random_key__.format(channel.id), generator)

		return generator

	def _set_seed(self, ctx: Channelable, seed = Optional[str]):
		channel = get_guild_channel(ctx.channel)
		if is_DM(channel):
			return
		generator = random.Random(seed)
		self.state.set(self.__state_random_key__.format(channel.id), generator)
