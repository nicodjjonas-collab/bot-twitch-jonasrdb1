import os
import twitchio
from twitchio.ext import commands

TOKEN = os.environ.get('TWITCH_TOKEN')
CANAL = os.environ.get('TWITCH_CANAL', 'jonasrdb')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CANAL])
    
    async def event_ready(self):
        print('Bot conectado a #' + CANAL)
        print('Esperando comandos...')
    
    @commands.command()
    async def comandos(self, ctx):
        await ctx.send('Bot funcionando! Comandos: !hola, !dado')
    
    @commands.command()
    async def hola(self, ctx):
        await ctx.send('Hola @' + ctx.author.name + '!')
    
    @commands.command()
    async def dado(self, ctx):
        import random
        n = random.randint(1, 6)
        await ctx.send('@' + ctx.author.name + ' tiro: ' + str(n))

bot = Bot()

if __name__ == '__main__':
    bot.run()
