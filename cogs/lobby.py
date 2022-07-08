import asyncio
from datetime import datetime, timedelta
import random
from typing import List
from disnake.ext import commands
import disnake

from core.enums import Server


class Lobby(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.lobbies = {}

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     lobby_category: disnake.CategoryChannel = self.bot.get_channel(Server.LOBBY_CAT)
    #     if lobby_category:
    #         for channel in lobby_category.voice_channels:
    #             if channel.members.__len__() < 1:
    #                 await channel.delete()

    @commands.Cog.listener('on_reaction_add')
    @commands.Cog.listener('on_reaction_remove')
    async def on_reaction_add(self, reaction: disnake.Reaction, _):
        lobby = next((self.lobbies[i] for i in self.lobbies if "message" in self.lobbies[i] and self.lobbies[i]["message"] == reaction.message.id and reaction.emoji == "➕"), None)

        if lobby:
            embed = next((i for i in reaction.message.embeds), None)
            
            if embed:
                users = await reaction.users().flatten()
                if self.bot.user in users:
                    users.remove(self.bot.user)
                print(lobby)
                embed.set_footer(text=f"Participants ({reaction.count-1}/{lobby['size']*2}): " + ', '.join([i.name for i in users]))
                await reaction.message.edit(embed=embed)

    
    @commands.guild_only()
    @commands.slash_command(
        name="create_lobby",
        description="Create a new league of legends lobby.",
        options=[
            disnake.Option(
                name="mode",
                description="The mode the game will take place!",
                type=disnake.OptionType.string,
                required=True,
                choices=[
                    disnake.OptionChoice(name="aram", value="❄️ ARAM ❄️"),
                    disnake.OptionChoice(name="rift", value="🌍 SUMMONER'S RIFT 🌍"),
                    disnake.OptionChoice(name="twisted_treeline", value="👀 FAHD'S BASEMENT 👀")
                ]
            ),
            disnake.Option(
                name="team_size",
                description="Team size for the lobby. Default: 5",
                type=disnake.OptionType.integer,
                min_value=1,
                max_value=5,
            ),
            disnake.Option(
                name="expiration",
                description="Expiration time for the lobby. Default: 30 mins",
                type=disnake.OptionType.integer,
                min_value=5
            )
        ]
    )
    async def create_lobby(self, inter:disnake.CommandInteraction, mode, team_size=5, expiration=30):
        if inter.author.id in self.lobbies:
            return await inter.send("You already have a lobby! Wait for it to expire.")

        team_size = int(team_size)
        expiration = int(expiration)

        await inter.send("Creating lobby...", ephemeral=True)
        
        embed = disnake.Embed(
            title=f"{inter.author.name}'s Lobby",
            description=f"{inter.author.mention} is hosting a **{team_size}v{team_size} Game**! React below with \➕ to participate! Teams will be created randomly once all slots are filled."
        )

        embed.add_field("⌛ Expiration", "This lobby expires <t:" + round((datetime.now()+timedelta(minutes=expiration)).timestamp()).__str__() + ":R>.")
        embed.add_field("🗺️ MODE", mode)
        
        embed.set_footer(text="No Participants, yet.")

        msg = await inter.channel.send("<@&711263948674170890>", embed=embed)

        await inter.edit_original_message("Lobby was created!")

        await msg.add_reaction("➕")

        self.lobbies[inter.author.id] = {
            "message": msg.id,
            "size": team_size
        }

        try:
            reaction, _ = await self.bot.wait_for(
                'reaction_add',
                check=lambda r,_: r.message.id == msg.id and r.emoji == "➕" and r.count == team_size*2+1,
                timeout=60*expiration
            )
        except asyncio.TimeoutError:
            return await msg.edit("Lobby was closed due to missing slots.", embed=None)

        users = await reaction.users().flatten()
        if self.bot.user in users:
            users.remove(self.bot.user)

        users: List[disnake.User] = random.sample(users, len(users))
        team1, team2 = users[:team_size], users[team_size:]

        lobby_category: disnake.CategoryChannel = self.bot.get_channel(Server.LOBBY_CAT)

        if not lobby_category or not isinstance(lobby_category, disnake.CategoryChannel): return await inter.channel.send("Failed to create lobby: MISSING LOBBY_CAT in Server ENUMS or category cannot be found.")

        team1_overwrites = {
            msg.guild.default_role: disnake.PermissionOverwrite(view_channel=False)
        }
        for user in team1:
            team1_overwrites[user] = disnake.PermissionOverwrite(view_channel=True, connect=True)

        team2_overwrites = {
            msg.guild.default_role: disnake.PermissionOverwrite(view_channel=False)
        }
        for user in team2:
            team2_overwrites[user] = disnake.PermissionOverwrite(view_channel=True, connect=True)

        team1_channel: disnake.VoiceChannel = await lobby_category.create_voice_channel(
            name=f"{inter.author.name}'s Game: TEAM 1",
            overwrites=team1_overwrites
        )
        team2_channel: disnake.VoiceChannel = await lobby_category.create_voice_channel(
            name=f"{inter.author.name}'s Game: TEAM 2",
            overwrites=team2_overwrites
        )

        await msg.reply("**GAME WAS CREATED!**\n" + ", ".join([user.mention for user in team1]) + " => Join " + team1_channel.mention + "\n" + ", ".join([user.mention for user in team2]) + " => Join " + team2_channel.mention + f"\n\n{inter.author.mention} send `game over` to close the lobby! **GLHF!**")

        msg: disnake.Message = await self.bot.wait_for('message', check=lambda m: m.author.id == inter.author.id and m.channel.id == inter.channel.id and m.content.lower() == "game over")

        await team1_channel.delete()
        await team2_channel.delete()

        return await msg.reply("Channels were deleted and game was closed, **GG!**") 

    @create_lobby.after_invoke
    async def clear_lobby(self, inter:disnake.CommandInteraction):
        if inter.author.id in self.lobbies:
            del self.lobbies[inter.author.id]
        
def setup(bot):
    bot.add_cog(Lobby(bot))