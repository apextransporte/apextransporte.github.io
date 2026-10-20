import io
import os

import discord

try:
    from PIL import Image
except ImportError:
    Image = None

JOBLOG_CHANNEL_ID = int(os.getenv("JOBLOG_CHANNEL_ID", "0"))
STAFF_CHANNEL_ID = int(os.getenv("STAFF_CHANNEL_ID", "0"))

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp")
MAX_BYTES = 15 * 1024 * 1024

NAME_MARKERS = (
    "midjourney", "dall-e", "dalle", "chatgpt", "gemini", "firefly",
    "generated", "imagefx", "leonardo", "ideogram", "stable_diffusion",
)

AI_MARKERS = (
    b"midjourney", b"dall-e", b"dalle", b"stable diffusion", b"stablediffusion",
    b"openai", b"chatgpt", b"gemini", b"adobe firefly", b"leonardo.ai",
    b"negative prompt", b"comfyui", b"invokeai", b"ideogram", b"c2pa", b"jumbf",
)

AI_SIZES = {
    (512, 512), (768, 768), (1024, 1024), (1024, 1536), (1536, 1024),
    (1024, 1792), (1792, 1024), (1344, 768), (768, 1344), (2048, 2048),
}


async def find_channel(bot, channel_id):
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except Exception as error:
        print(f"Channel {channel_id} error: {error!r}", flush=True)
        return None


def check_image(filename, data):
    reasons = []
    name = filename.lower()
    for word in NAME_MARKERS:
        if word in name:
            reasons.append(f"File name contains {word}")
    lowered = data.lower()
    for marker in AI_MARKERS:
        if marker in lowered:
            reasons.append(f"Hidden file data contains {marker.decode()}")
    if Image is not None:
        try:
            with Image.open(io.BytesIO(data)) as img:
                if img.size in AI_SIZES:
                    reasons.append(f"Image size {img.size[0]}x{img.size[1]} matches AI tools")
        except Exception:
            pass
    return reasons


async def guard(bot, message):
    if message.author.bot:
        return
    if not JOBLOG_CHANNEL_ID or message.channel.id != JOBLOG_CHANNEL_ID:
        return

    images = [a for a in message.attachments if a.filename.lower().endswith(IMAGE_TYPES)]
    if not images:
        return

    flagged = []
    for attachment in images:
        if attachment.size > MAX_BYTES:
            continue
        data = await attachment.read()
        reasons = check_image(attachment.filename, data)
        if reasons:
            flagged.append((attachment, data, reasons))

    if not flagged:
        try:
            await message.add_reaction("\u2705")
        except Exception as error:
            print(f"Reaction error: {error!r}", flush=True)
        return

    try:
        await message.add_reaction("\u274C")
    except Exception as error:
        print(f"Reaction error: {error!r}", flush=True)

    try:
        await message.delete()
    except Exception as error:
        print(f"Delete error: {error!r}", flush=True)

    try:
        await message.channel.send(
            f"{message.author.mention} Your screenshot was removed. "
            "Post a real in-game screenshot of your job.",
            delete_after=20,
        )
    except Exception as error:
        print(f"Warning error: {error!r}", flush=True)

    staff = await find_channel(bot, STAFF_CHANNEL_ID)
    if staff is None:
        print("Staff channel not found. Check STAFF_CHANNEL_ID.", flush=True)
        return

    for attachment, data, reasons in flagged:
        extension = os.path.splitext(attachment.filename)[1] or ".png"
        file_name = f"flagged{extension}"
        embed = discord.Embed(
            title="Possible AI screenshot removed",
            color=discord.Color.from_rgb(200, 16, 46),
        )
        embed.add_field(name="Driver", value=f"{message.author.mention} ({message.author})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Reasons", value="\n".join(f"- {r}" for r in reasons)[:1000], inline=False)
        embed.set_image(url=f"attachment://{file_name}")
        try:
            await staff.send(embed=embed, file=discord.File(io.BytesIO(data), filename=file_name))
        except Exception as error:
            print(f"Staff alert error: {error!r}", flush=True)
