import logging
import logging.handlers
import interactions
from interactions import listen, Intents, Permissions, slash_default_member_permission
from interactions.api.events import Ready
import os
import time
from pytimeparse.timeparse import timeparse
import datetime
import asyncio # not currently in use but might later

if not os.path.exists("logs"):
    os.makedirs("logs")

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

fileHandler = logging.handlers.TimedRotatingFileHandler(
    filename="logs/jailer.log", 
    when="midnight",
    backupCount=28, 
    encoding="utf-8")
fileHandler.setFormatter(formatter)
fileHandler.setLevel(logging.DEBUG)

streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.INFO)
streamHandler.setFormatter(formatter)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers= [fileHandler, streamHandler],
    level=logging.DEBUG
)

cls_log = logging.getLogger("JailerLogger")

bot = interactions.Client(
    intents=Intents.ALL,    
    token=os.environ["DISCORD_TOKEN"],
    default_scope=os.environ["GUILD_ID"],
    sync_interactions=True,
    logger=cls_log,
    send_command_tracebacks=False
)

# array of users currently in jail
users = []

# functions
def parse_duration(duration: str) -> datetime.timedelta:
    duration = duration.lower()
    cls_log.debug(f'Parsing duration {duration}')
    seconds = timeparse(duration)
    cls_log.debug(f'Parsed duration {duration} seconds')
    return datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    
def jail_user(user: str, duration: datetime.timedelta, annoy: bool = False):
    users.append({
        "user": user,
        "duration": duration,
        "annoy_user": annoy,
        "start_time": datetime.datetime.now(),
        "annoyed_last": datetime.datetime.now()
    })
    cls_log.info(users)

def release_user(user: interactions.User):
    for u in users:
        if u["user"] == user:
            cls_log.info(f'Releasing {user}')
            users.remove(u)

async def annoy_user(user: interactions.User, start_time: datetime.datetime, duration: datetime.timedelta):
    await interactions.Member.timeout(user, None)
    time.sleep(5)
    await interactions.Member.timeout(user, duration - (datetime.datetime.now() - start_time))

def list_users():
    return users

@interactions.listen()
async def on_startup():
    cls_log.info("Bot is ready")
    check_jail.start()

@interactions.Task.create(interactions.IntervalTrigger(seconds=5))
async def check_jail():
    cls_log.info("Checking jail")
    for u in users:
        if datetime.datetime.now() > u['duration']:
            release_user(u["user"])
        if u["annoy_user"] and (datetime.datetime.now() - u["annoyed_last"]) >= datetime.timedelta(seconds=60): # annoy the user every minute
            u["annoyed_last"] = datetime.datetime.now()
            await annoy_user(u["user"], u["start_time"], u["duration"])

@interactions.slash_command(name="jail", description="Jail a user")
@interactions.slash_default_member_permission(Permissions.MANAGE_CHANNELS)
@interactions.slash_option(name="user", description="The user to jail", opt_type=interactions.OptionType.USER, required=True)
@interactions.slash_option(name="duration", description="The duration of the jail sentence", opt_type=interactions.OptionType.STRING, required=True)
@interactions.slash_option(name="annoy", description="Annoy the user", opt_type=interactions.OptionType.BOOLEAN, required=False)
async def jail(ctx: interactions.SlashContext, user: str, duration: str, annoy: bool = False):
    duration = parse_duration(duration)
    cls_log.info(f'Jailing {user} for {duration} with annoy={annoy}')
    jail_user(user, duration, annoy)
    cls_log.error(f'Error jailing user: {user}')
    await interactions.Member.timeout(user, duration)
    await ctx.send(f'Jailing {user} for {duration} with annoy={annoy}')

@interactions.slash_command(name="release", description="Release a user from jail")
@interactions.slash_default_member_permission(Permissions.MANAGE_CHANNELS)
@interactions.slash_option(name="user", description="The user to jail", opt_type=interactions.OptionType.USER, required=True)
async def release(ctx: interactions.SlashContext, user: interactions.User):
    cls_log.info(f'Releasing {user}')
    release_user(user)
    await interactions.Member.timeout(user, None)
    await ctx.send(f'Releasing {user}')

@interactions.slash_command(name="list", description="List all users in jail")
@interactions.slash_default_member_permission(Permissions.MANAGE_CHANNELS)
async def list(ctx: interactions.SlashContext):
    cls_log.info(f'Listing users in jail')
    users = list_users()
    if len(users) == 0:
        await ctx.send("No users in jail")
    else:
        msg = "Users in jail:\n"
        for u in users:
            msg += f'{u["user"]} until {u["duration"]}\n'
        await ctx.send(msg)

# start the bot
bot.start()