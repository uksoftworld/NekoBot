from discord.ext import commands
import discord
import rethinkdb as r
import aiohttp
from prettytable import PrettyTable

import random
import string
import time
import logging

from config import webhook_id, webhook_token
from .utils.hastebin import post as haste
import gettext

log = logging.getLogger()

class Donator:

    def __init__(self, bot):
        self.bot = bot
        self.lang = {}
        # self.languages = ["french", "polish", "spanish", "tsundere", "weeb"]
        self.languages = ["tsundere", "weeb", "chinese"]
        for x in self.languages:
            self.lang[x] = gettext.translation("donator", localedir="locale", languages=[x])

    async def _get_text(self, ctx):
        lang = await self.bot.get_language(ctx)
        if lang:
            if lang in self.languages:
                return self.lang[lang].gettext
            else:
                return gettext.gettext
        else:
            return gettext.gettext

    def id_generator(self, size=7, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    async def __post_to_hook(self, embed:discord.Embed):
        async with aiohttp.ClientSession() as cs:
            webhook = discord.Webhook.from_url("https://discordapp.com/api/webhooks/%s/%s" % (webhook_id, webhook_token,),
                                               adapter=discord.AsyncWebhookAdapter(cs))
            await webhook.send(embed=embed)

    async def __has_donated(self, user:int):
        all_data = await r.table("donator").order_by("id").run(self.bot.r_conn)
        users = []
        for data in all_data:
            users.append(data.get("user", "none"))
        if str(user) in users:
            return True
        else:
            return False

    async def on_message(self, message):
        if not message.guild:
            return
        if message.guild.id == 221989003400970241 and message.channel.id == 431887286246834178 and len(message.embeds) >= 1:
            embed = message.embeds[0]
            if embed.title == "Patreon Update.":
                user = embed.footer.text
                if isinstance(user, discord.Embed.Empty):
                    return
                fuckingweeb = self.bot.get_user(270133511325876224)
                if embed.description.startswith("pledges:delete"):
                    keys = await r.table("donator").order_by("").run(self.bot.r_conn)
                    keys = [x for x in keys if x.get("user") == str(user)][0]
                    await r.table("donator").get(str(keys)).delete().run(self.bot.r_conn)
                    embed = discord.Embed(color=0xff6f3f, title="Token Deleted",
                                          description=f"```css\n"
                                                      f"Key: [ {keys} ] \n"
                                                      f"```")
                    await self.__post_to_hook(embed)
                    await fuckingweeb.send("Deleted key for %s" % user)
                elif embed.description.startswith("pledges:create"):
                    x1 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
                    x2 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
                    x3 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
                    token = f"{x1}-{x2}-{x3}"
                    data = {
                        "id": token,
                        "user": str(user),
                        "created_at": int(time.time())
                    }
                    await r.table("donator").insert(data).run(self.bot.r_conn)
                    await fuckingweeb.send("Given key for %s" % user)
                    user = await self.bot.get_user_info(int(user))
                    await self.__post_to_hook(discord.Embed(color=0xff6f3f, title="Token Accepted",
                                                            description="```css\nUser: %s (%s)\nToken [ %s ]\n```" % (user, user.id, token,)))
                    await user.send("Thank you for donating, perks should now be active for you ❤")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sendkey(self, ctx, UserID:int, *, key: str):
        """Send a user their donation key."""
        await ctx.message.add_reaction("👌")
        user = await self.bot.get_user_info(UserID)
        await user.send(f"Your donation key:\n`{key}`")

    @commands.command(name='trapcard')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def donator_trapcard(self, ctx, user: discord.Member):
        """Trap a user!"""
        await ctx.trigger_typing()
        _ = await self._get_text(ctx)

        if not await self.__has_donated(ctx.author.id):
            return await ctx.send(_("You need to be a **donator** to use this command."))

        async with aiohttp.ClientSession() as session:
            url = f"https://nekobot.xyz/api/imagegen" \
                  f"?type=trap" \
                  f"&name={user.name}" \
                  f"&author={ctx.author.name}" \
                  f"&image={user.avatar_url_as(format='png')}"
            async with session.get(url) as response:
                t = await response.json()
                await ctx.send(embed=discord.Embed(color=0xDEADBF).set_image(url=t['message']))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def createkey(self, ctx):
        """Create a key"""
        await ctx.trigger_typing()
        x1 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
        x2 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
        x3 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
        token = f"{x1}-{x2}-{x3}"
        await ctx.send(token)
        data = {
            "id": token,
            "user": "",
            "created_at": int(time.time())
        }
        await r.table("donator").insert(data).run(self.bot.r_conn)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def redeem(self, ctx, *, key: str):
        """Redeem your donation key"""
        await ctx.trigger_typing()
        _ = await self._get_text(ctx)

        data = await r.table("donator").get(key).run(self.bot.r_conn)
        if not data:
            await self.__post_to_hook(discord.Embed(color=0xff6f3f, title="Invalid Token",
                                                    description="```css\n%s (%s) input an invalid token %s\n```" % (ctx.author, ctx.author.id, key,)))
            return await ctx.send(_("**Not a valid key...**"))

        if not data["user"]:
            await self.__post_to_hook(discord.Embed(color=0xff6f3f, title="Token Accepted",
                                                    description="```css\nUser: %s (%s)\nToken [ %s ]\n```" % (ctx.author, ctx.author.id, key,)))
            await r.table("donator").get(key).update({"user": str(ctx.author.id)}).run(self.bot.r_conn)
            await ctx.send(_("**Token Accepted!**"))
        else:
            await self.__post_to_hook(discord.Embed(color=0xff6f3f, title="Invalid Token - In use",
                                                    description="```css\n%s (%s) input an invalid token %s\n```" % (
                                                    ctx.author, ctx.author.id, key,)))
            return await ctx.send(_("**Token is already in use.**"))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def keys(self, ctx):
        """View all keys + expiry"""
        await ctx.trigger_typing()
        allkeys = await r.table("donator").order_by("id").run(self.bot.r_conn)
        table = PrettyTable()
        table.field_names = ["User", "Key"]
        for key in allkeys:
            table.add_row([str(key["user"]), str(key["id"])])
        x = await haste(str(table))
        await ctx.send(x)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def delkey(self, ctx, *, key: str):
        """Delete a key"""
        await ctx.trigger_typing()

        await r.table("donator").get(key).delete().run(self.bot.r_conn)
        embed = discord.Embed(color=0xff6f3f, title="Token Deleted",
                              description=f"```css\n"
                                          f"Key: [ {key} ] \n"
                                          f"```")
        await self.__post_to_hook(embed)

        await ctx.send("Deleted.")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def donate(self, ctx):
        await ctx.trigger_typing()
        _ = await self._get_text(ctx)

        if not await self.__has_donated(ctx.author.id):
            await ctx.send(_("You can donate at <https://www.patreon.com/NekoBot>!"))
        else:
            await ctx.send(_("You have already donated <:ChocoHappy:429538812855582721><a:rainbowNekoDance:462373594555613214>"))

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(aliases=["autolood", "autolewd"])
    async def autolooder(self, ctx, channel:discord.TextChannel=None):
        """
        Enable/Disable the autolooder for your server, mention an already added channel to disable.
        Example:
            n!autolooder #autolood_channel
            or
            n!autolooder autolood_channel"""
        _ = await self._get_text(ctx)

        if await r.table("autolooder").get(str(ctx.guild.id)).run(self.bot.r_conn):
            await r.table("autolooder").get(str(ctx.guild.id)).delete().run(self.bot.r_conn)
            return await ctx.send(_("I have disable the autolooder for you <:lurk:356825018702888961>"))

        if not await self.__has_donated(ctx.author.id):
            return await ctx.send(_("You have not donated :c, you can donate at <https://www.patreon.com/NekoBot> <:AwooHappy:471598416238215179>"))

        if not channel:
            return await self.bot.send_cmd_help(ctx)

        data = {
            "id": str(ctx.guild.id),
            "channel": str(channel.id),
            "user": str(ctx.author.id),
            "choices": [
                "hentai",
                "neko",
                "hentai_anal",
                "lewdneko",
                "lewdkitsune"
            ]
        }
        await r.table("autolooder").insert(data).run(self.bot.r_conn)
        await ctx.send(_("Enabled autolooder for `%s`!") % channel.name)


    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.command(aliases=["autoloodersetting", "autolewdsetting", "autoloodsettings", "autolewdsettings", "autoloodersettings"])
    async def autoloodsetting(self, ctx, imgtype: str = None):
        """Toggle autolood options for the current servers autolewder

        Image Types: pgif, 4k, hentai, holo, lewdneko, neko, lewdkitsune, kemonomimi, anal, hentai_anal, gonewild, kanna, ass, pussy, thigh
        Example: n!autoloodtoggle holo"""
        _ = await self._get_text(ctx)

        data = await r.table("autolooder").get(str(ctx.guild.id)).run(self.bot.r_conn)
        if not data:
            return await ctx.send("Autolooder is not enabled on this server")

        if imgtype is None:
            return await ctx.send("Enabled Types: %s" % ", ".join(["`%s`" % i for i in data.get("choices", [])]))

        options = ["pgif", "4k", "hentai", "holo", "lewdneko", "neko", "lewdkitsune", "kemonomimi", "anal",
                   "hentai_anal", "gonewild", "kanna", "ass", "pussy", "thigh"]

        imgtype = imgtype.lower()
        if imgtype not in options:
            return await ctx.send("Not a valid type, valid types: %s" % ", ".join(["`%s`" % i for i in options]))

        if imgtype in data.get("choices", []):
            newchoices = []
            for choice in data.get("choices", []):
                if choice != imgtype:
                    newchoices.append(choice)
        else:
            newchoices = data.get("choices", []) + [imgtype]

        await r.table("autolooder").get(str(ctx.guild.id)).update({"choices": newchoices}).run(self.bot.r_conn)
        await ctx.send("Toggled option for %s!" % imgtype)

def setup(bot):
    bot.add_cog(Donator(bot))