import os
import random
import twitchio
from twitchio.ext import commands

TOKEN = os.environ.get('TWITCH_TOKEN')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CANAL])
    
    async def event_ready(self):
        print(f'Bot listo en #{CANAL}')
    
    @commands.command()
    async def comandos(self, ctx):
        await ctx.send('INFO: !redes, !sobre, !festero, !dado, !moneda, !vf')
    
    @commands.command()
    async def redes(self, ctx):
        await ctx.send('Sigueme: Kick: https://kick.com/jonasrdboficial | YouTube: https://www.youtube.com/@JonasRDB')
    
    @commands.command()
    async def sobre(self, ctx):
        await ctx.send('JONAS RDB // HARD DANCE. DJ alicantino desde 1994. +30 anos de Hard Dance y Remember.')
    
    @commands.command()
    async def festero(self, ctx):
        p = random.randint(0, 100)
        await ctx.send(f'@{ctx.author.name} esta al {p}% de festero!')
    
    @commands.command()
    async def dado(self, ctx):
        n = random.randint(1, 6)
        await ctx.send(f'@{ctx.author.name} tiro el dado: {n}')
    
    @commands.command()
    async def moneda(self, ctx):
        r = random.choice(['CARA', 'CRUZ'])
        await ctx.send(f'@{ctx.author.name} lanzo la moneda: {r}')

bot = Bot()

if __name__ == '__main__':
    bot.run()
