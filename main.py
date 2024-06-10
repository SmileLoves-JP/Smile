import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

LOG_FILE = 'log.json'

def save_log_channels(text_channel_id, forum_channel_id):
    with open(LOG_FILE, 'w') as f:
        json.dump({'log_text_channel_id': text_channel_id, 'log_forum_channel_id': forum_channel_id}, f)

def load_log_channels():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            data = json.load(f)
            return data.get('log_text_channel_id'), data.get('log_forum_channel_id')
    return None, None

def save_role_settings(forum_channel_id, role_id):
    with open(LOG_FILE, 'r') as f:
        data = json.load(f)
    data['role_settings'] = {'forum_channel_id': forum_channel_id, 'role_id': role_id}
    with open(LOG_FILE, 'w') as f:
        json.dump(data, f)

def load_role_settings():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            data = json.load(f)
            return data.get('role_settings', {}).get('forum_channel_id'), data.get('role_settings', {}).get('role_id')
    return None, None

def clear_log_channels():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            data = json.load(f)
        data['log_text_channel_id'] = None
        data['log_forum_channel_id'] = None
        with open(LOG_FILE, 'w') as f:
            json.dump(data, f)

def clear_role_settings():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            data = json.load(f)
        data['role_settings'] = {'forum_channel_id': None, 'role_id': None}
        with open(LOG_FILE, 'w') as f:
            json.dump(data, f)

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_text_channel_id, self.log_forum_channel_id = load_log_channels()
        self.role_forum_channel_id, self.role_id = load_role_settings()
        self.log_text_channel = None
        self.log_forum_channel = None
        self.role = None

    async def setup_hook(self):
        if self.log_text_channel_id:
            self.log_text_channel = self.get_channel(self.log_text_channel_id)
        if self.log_forum_channel_id:
            self.log_forum_channel = self.get_channel(self.log_forum_channel_id)
        await self.tree.sync()

    async def on_ready(self):
        print(f'{self.user} としてログインしました')

    async def on_message(self, message):
        if not self.log_text_channel:
            return

        if isinstance(message.channel, discord.Thread) and isinstance(message.channel.parent, discord.ForumChannel):
            tags = [tag.name for tag in message.channel.applied_tags]
            embed = discord.Embed(
                title=message.channel.name,
                description=message.content,
                timestamp=message.created_at,
                color=discord.Color.blue()  # 埋め込みの色を水色に設定
            )
            embed.set_thumbnail(url=message.author.avatar.url)  # サムネイルとしてユーザーのアイコン画像を設定
            embed.add_field(name="フォーラムのURL", value=message.jump_url, inline=False)
            embed.add_field(name="タグ", value=', '.join(tags), inline=False)
            embed.add_field(name="投稿したユーザー", value=message.author.name, inline=False)
            embed.set_footer(text=f"© 2024 aohime shop")
            await self.log_text_channel.send(embed=embed)

            # フォーラムチャンネルでの投稿に対してロールを付与
            if message.channel.parent.id == self.role_forum_channel_id:
                guild = message.guild
                role = guild.get_role(self.role_id)
                if role:
                    await message.author.add_roles(role)
                    print(f'ロール {role.name} が {message.author.name} に付与されました')

client = MyClient(intents=intents)

class LogCommands(app_commands.Group):
    @app_commands.command(name="channel", description="ログチャンネルを設定します")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        client.log_text_channel = channel
        client.log_text_channel_id = channel.id
        save_log_channels(client.log_text_channel_id, client.log_forum_channel_id)
        await interaction.response.send_message(f'ログチャンネルが {channel.mention} に設定されました')

    @app_commands.command(name="forum", description="ログとして記録するフォーラムチャンネルを設定します")
    async def set_log_forum(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        client.log_forum_channel = channel
        client.log_forum_channel_id = channel.id
        save_log_channels(client.log_text_channel_id, client.log_forum_channel_id)
        await interaction.response.send_message(f'フォーラムチャンネルが {channel.mention} に設定されました')

    @app_commands.command(name="clear_log", description="設定したログチャンネルとフォーラムチャンネルのIDを削除します")
    async def clear_log_channels_command(self, interaction: discord.Interaction):
        client.log_text_channel = None
        client.log_text_channel_id = None
        client.log_forum_channel = None
        client.log_forum_channel_id = None
        clear_log_channels()
        await interaction.response.send_message('ログチャンネルとフォーラムチャンネルの設定が削除されました')

log_commands = LogCommands(name="set_log")
client.tree.add_command(log_commands)

class ConfigCommands(app_commands.Group):
    @app_commands.command(name="role", description="フォーラムチャンネルで投稿したユーザーに付与するロールを設定します")
    async def set_role(self, interaction: discord.Interaction, forum_channel: discord.ForumChannel, role: discord.Role):
        client.role_forum_channel_id = forum_channel.id
        client.role_id = role.id
        save_role_settings(forum_channel.id, role.id)
        await interaction.response.send_message(f'フォーラムチャンネル {forum_channel.mention} に投稿するユーザーにロール {role.mention} を付与するように設定しました')

    @app_commands.command(name="clear_role", description="設定したロールを削除します")
    async def clear_role_settings_command(self, interaction: discord.Interaction):
        client.role_forum_channel_id = None
        client.role_id = None
        clear_role_settings()
        await interaction.response.send_message('設定されたロールが削除されました')

config_commands = ConfigCommands(name="config")
client.tree.add_command(config_commands)

client.run(TOKEN)