import re
import random
import discord
from discord import app_commands
import threading
from flask import Flask
import os
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()


TOKEN = os.getenv("TOKEN")

initiative_sessions = {}


class DiceBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


bot = DiceBot()

# UNIVERSAL DICE ENGINE


def roll_expression(expression: str):
    expression = expression.replace(" ", "").lower()

    pattern = r'([+-]?)(\d*)d(\d+)(kh1|kl1)?|([+-]?\d+)'
    matches = re.finditer(pattern, expression)

    total = 0
    breakdown = []

    for match in matches:
        sign = -1 if match.group(1) == "-" else 1

        if match.group(3):
            rolls = int(match.group(2)) if match.group(2) else 1
            sides = int(match.group(3))
            keep = match.group(4)

            results = [random.randint(1, sides) for _ in range(rolls)]

            if keep == "kh1":
                chosen = max(results)
                subtotal = chosen * sign
                breakdown.append(f"{rolls}d{sides}kh1 → {results} → {chosen}")

            elif keep == "kl1":
                chosen = min(results)
                subtotal = chosen * sign
                breakdown.append(f"{rolls}d{sides}kl1 → {results} → {chosen}")

            else:
                subtotal = sum(results) * sign
                breakdown.append(f"{rolls}d{sides}: {results} = {subtotal}")

            total += subtotal

        elif match.group(5):
            value = int(match.group(5))
            total += value
            breakdown.append(str(value))

    return total, breakdown, expression


# =========================================================
# /ROLL COMMAND
# =========================================================

@bot.tree.command(name="roll", description="Roll dice (e.g. 3d6+5d4+3)")
@app_commands.describe(expression="Dice expression like 3d6+5d4+3")
async def roll(interaction: discord.Interaction, expression: str):

    try:
        total, breakdown, final_notation = roll_expression(expression)

        embed = discord.Embed(
            description=f"\n# 🎲 {total}\n",
            color=discord.Color.blue()
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        embed.add_field(
            name="Notation",
            value=f"`{final_notation}`",
            inline=False
        )

        embed.add_field(
            name="Breakdown",
            value="\n".join(breakdown),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            f"Error: {str(e)}",
            ephemeral=True
        )



# INITIATIVE SYSTEM


@bot.tree.command(name="initiative", description="Roll initiative (e.g. 2d20kh1+4 Ryze)")
@app_commands.describe(
    expression="Dice expression (e.g. 2d20kh1+4)",
    name="Character name (optional)"
)
async def initiative(
    interaction: discord.Interaction,
    expression: str,
    name: str = None
):

    try:
        guild_id = interaction.guild.id

        # Determine character name
        if name:
            character_name = name
        else:
            # Use server nickname if available
            character_name = interaction.user.nick or interaction.user.display_name

        total, breakdown, final_notation = roll_expression(expression)

        if guild_id not in initiative_sessions:
            initiative_sessions[guild_id] = []

        # Store as (name, total)
        initiative_sessions[guild_id].append((character_name, total))

        embed = discord.Embed(
            description=f"\n# ⚔️ {total}\n",
            color=discord.Color.red()
        )

        embed.set_author(
            name=character_name,
            icon_url=interaction.user.display_avatar.url
        )

        embed.add_field(
            name="Notation",
            value=f"`{final_notation}`",
            inline=False
        )

        embed.add_field(
            name="Breakdown",
            value="\n".join(breakdown),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            f"Error: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="endinitiative", description="End initiative and show turn order")
async def endinitiative(interaction: discord.Interaction):

    guild_id = interaction.guild.id

    if guild_id not in initiative_sessions or not initiative_sessions[guild_id]:
        await interaction.response.send_message(
            "No initiative rolls found.",
            ephemeral=True
        )
        return

    session = initiative_sessions[guild_id]

    # Sort descending
    sorted_order = sorted(session, key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="⚔️ Combat Initiative Order",
        color=discord.Color.gold()
    )

    description = ""
    for index, (name, total) in enumerate(sorted_order, start=1):
        description += f"**{index}.** {name} — **{total}**\n"

    embed.description = description

    # Reset session
    initiative_sessions[guild_id] = []

    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)