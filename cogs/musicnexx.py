import discord
import asyncio
import yt_dlp
import json
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime

# Load config
with open('data.json', 'r') as f:
    config = json.load(f)

queues = {}
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

class MusicNexx(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_channel_id = config.get("ALLOWED_CHANNEL_ID")

    async def play_song(self, interaction, url):
        guild_id = interaction.guild.id
        if guild_id not in queues:
            queues[guild_id] = []

        try:
            data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            if 'entries' in data:  # playlist
                for entry in data['entries']:
                    queues[guild_id].append(entry['webpage_url'])
                await interaction.followup.send("Playlist added to queue.")
                await self.play_next(interaction)
                return

            song_url = data['url']
            title = data['title']
            thumbnail = data.get('thumbnail', '')
            duration = data['duration']
            artist = data.get('uploader', 'Unknown Artist')

            voice_client = interaction.guild.voice_client
            player = discord.FFmpegOpusAudio(song_url, **ffmpeg_options)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop))

            embed = discord.Embed(
                title="🎶 Now Playing 🎶",
                description=' '.join(title.split()[:4]),
                color=discord.Color.from_rgb(255, 229, 236)
            )
            embed.set_thumbnail(url=thumbnail)
            embed.add_field(name="**Duration**", value=f"{duration // 60}:{duration % 60}", inline=False)
            embed.add_field(name="**Artist**", value=artist, inline=False)
            embed.add_field(name="**Requested by**", value=interaction.user.display_name, inline=False)
            embed.add_field(name="**Requested at**", value=datetime.now().strftime('%H:%M:%S'), inline=False)
            embed.set_footer(text="Music Bot | Enjoy your time!", icon_url=interaction.user.avatar.url)

            await interaction.followup.send(embed=embed, view=ControlButtons(interaction))

        except Exception as e:
            print(f"Error while playing song: {e}")
            await interaction.followup.send("❌ Error while playing song.")

    async def play_next(self, interaction):
        guild_id = interaction.guild.id
        if guild_id in queues and queues[guild_id]:
            next_url = queues[guild_id].pop(0)
            await self.play_song(interaction, next_url)
        else:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.disconnect()

    @discord.app_commands.command(name="play", description="Play music from a URL")
    async def play(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        if interaction.channel.id != self.allowed_channel_id:
            await interaction.followup.send("❗ Use this command in the music channel only.", ephemeral=True)
            return

        if not interaction.user.voice:
            await interaction.followup.send("🔊 Join a voice channel first!", ephemeral=True)
            return

        if interaction.guild.voice_client is None:
            await interaction.user.voice.channel.connect()

        vc = interaction.guild.voice_client
        if vc.is_playing():
            queues[interaction.guild.id].append(url)
            await interaction.followup.send("✅ Added to the queue.")
        else:
            await self.play_song(interaction, url)

class ControlButtons(View):
    def __init__(self, interaction):
        super().__init__()
        self.interaction = interaction

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        vc = self.interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
        await interaction.response.defer()

    @discord.ui.button(label="Resume", style=discord.ButtonStyle.success)
    async def resume_button(self, interaction: discord.Interaction, button: Button):
        vc = self.interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
        await interaction.response.defer()

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        vc = self.interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        vc = self.interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        queues.pop(self.interaction.guild.id, None)
        await interaction.response.defer()

async def setup(bot):
    await bot.add_cog(MusicNexx(bot))
