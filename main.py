import discord
from discord import app_commands
from discord.ext import commands
import os
import dotenv

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot invite link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
    await bot.add_cog(EventCommand(bot))
    try:
        print("Syncing commands...")
        await bot.tree.sync()
        print("Commands synced successfully!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

tree = bot.tree

@tree.command(name="bot_refresh", description="Refresh and sync all bot commands")
async def bot_refresh(interaction: discord.Interaction):
    if interaction.user.id != 748739492856332376:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Successfully synced {len(synced)} commands!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to sync commands: {e}", ephemeral=True)

class EventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_config = {}
        try:
            with open('event_config.json', 'r') as f:
                import json
                self.event_config = json.load(f)
        except FileNotFoundError:
            pass

    def save_config(self):
        with open('event_config.json', 'w') as f:
            import json
            json.dump({str(k): v for k, v in self.event_config.items()}, f)

    @app_commands.command(name="event_setup", description="Setup event configuration")
    @app_commands.describe(role_id="Role ID to be mentioned for events", queue_channel="Channel where events should be queued")
    @app_commands.default_permissions(administrator=True)
    async def event_setup(self, interaction: discord.Interaction, role_id: str, queue_channel: str):
        try:
            self.event_config[str(interaction.guild_id)] = {
                "role_id": role_id,
                "queue_channel": queue_channel.strip("<#>")
            }
            self.save_config()
            await interaction.response.send_message("Event configuration has been saved! ✅", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to save configuration: {str(e)}", ephemeral=True)

    @app_commands.command(name="event", description="Submit an event donation")
    @app_commands.describe(event="Type of event", message="Extra event info", link="Message link")
    async def event(self, interaction: discord.Interaction, event: str, message: str, link: str):
        if str(interaction.guild_id) not in self.event_config:
            await interaction.response.send_message("Please ask an administrator to set up the event system first using /event_setup", ephemeral=True)
            return

        config = self.event_config[str(interaction.guild_id)]
        queue_channel = self.bot.get_channel(int(config["queue_channel"]))
        if not queue_channel:
            await interaction.response.send_message("Queue channel not found. Contact an admin.", ephemeral=True)
            return

        embed = discord.Embed(title="📅 | Event Pending", color=discord.Color.blue())
        embed.add_field(name="🎪 Event", value=event, inline=False)
        embed.add_field(name="🏆 Other Info", value=f"msg: {message}", inline=False)
        embed.add_field(name="🔗 Message Link", value=f"[Click here]({link})", inline=False)
        embed.add_field(name="😊 Donor", value=interaction.user.mention, inline=False)
        embed.set_footer(text=str(interaction.user.id))
        embed.set_thumbnail(url=interaction.user.avatar.url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.success, custom_id="accept_event"))
        view.add_item(discord.ui.Button(label="Deny", style=discord.ButtonStyle.danger, custom_id="deny_event"))

        await queue_channel.send(
            content=f"<@&{config['role_id']}> {interaction.user.mention} would like to donate for an event.",
            embed=embed,
            view=view
        )
        await interaction.response.send_message("Event has been queued! ✅", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not hasattr(interaction, 'data') or not interaction.data.get('custom_id'):
        return
        
    custom_id = interaction.data.get('custom_id')
    if custom_id.startswith("accept_") or custom_id.startswith("deny_"):
        action, type_ = custom_id.split("_")
        status = "accepted" if action == "accept" else "denied"
        color = discord.Color.green() if action == "accept" else discord.Color.red()
        try:
            await interaction.response.send_message(f"{type_.capitalize()} {status}! ✅" if action == "accept" else f"{type_.capitalize()} denied! ❌", ephemeral=True)
            original_msg = await interaction.channel.fetch_message(interaction.message.id)
            embed = original_msg.embeds[0]
            embed.title = embed.title.replace("Pending", status.capitalize())
            embed.color = color
            await original_msg.edit(embed=embed, view=None)
        except Exception:
            pass

bot.run(os.environ["TOKEN"])
