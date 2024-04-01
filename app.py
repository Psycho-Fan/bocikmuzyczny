import discord
from discord.ext import commands
import os
import yt_dlp as youtube_dl
from dotenv import load_dotenv
import asyncio

load_dotenv()
DISCORD_TOKEN = os.getenv("discord_token")

# Set up intents
intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!>', intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'outtmpl': 'music/%(title)s.%(ext)s',  # Specify the folder and file template
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, volume=0.5):  
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename), data=data, volume=volume)  

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Streaming(name="Music Party", url="https://psychoo.site/"))

@bot.command(name='play', help='Plays a song and joins the voice channel with deafen')
async def play(ctx, *args):
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client

        if not voice_channel or not voice_channel.is_connected():
            if not ctx.message.author.voice:
                await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
                return
            else:
                channel = ctx.message.author.voice.channel
                voice_channel = await channel.connect()

        if args:
            query = ' '.join(args)
            # Check if the query is a direct file path
            if os.path.isfile(f'music/{query}'):
                filename = f'music/{query}'
            else:
                filename = await YTDLSource.from_url(query, loop=bot.loop)

            if isinstance(filename, str):
                source = discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename)
                voice_channel.play(source)
                embed = discord.Embed(title=f'Now playing: {filename}', color=0x00ff00)
                await ctx.send(embed=embed)
            elif isinstance(filename, YTDLSource):
                voice_channel.play(filename)
                embed = discord.Embed(title=f'Now playing: {filename.title}', color=0x00ff00)
                await ctx.send(embed=embed)
        else:
            await ctx.send("Please provide a song name or file path.")
    except Exception as e:
        print(e)
        await ctx.send("An error occurred. Please make sure the bot is connected to a voice channel.")


@bot.command(name='list', help='Lists the available music in the "music" folder')
async def list_music(ctx):
    music_files = [f for f in os.listdir('music') if f.endswith(('.mp3', '.webm', '.m4a'))]
    if music_files:
        music_list = '\n'.join(music_files)
        await ctx.send(f'Available music in the "music" folder:\n```\n{music_list}\n```')
    else:
        await ctx.send('No music found in the "music" folder.')

@bot.command(name='skip', help='Skips the currently playing song')
async def skip(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client

    if voice_channel.is_playing():
        voice_channel.stop()
        await ctx.send('Skipped the current song.')
    else:
        await ctx.send('There is no song currently playing to skip.')

bot.run(DISCORD_TOKEN)
