import disnake
from random import randint
from typing import List, Dict


async def create_bot_author_embed(**kwargs) -> disnake.Embed:
    """Create a bot specific discord Embed."""
    embed = disnake.Embed(**kwargs)
    if not embed.color:
        embed.colour = _get_random_color()
    return embed


def _get_random_color():
    """Retrieves a random hex color."""
    r = lambda: randint(0, 255)
    return int(
        ("%02X%02X%02X" % (r(), r(), r())), 16
    )


async def add_embed_inline_fields(
    embed: disnake.Embed, fields: Dict[str, str]
) -> disnake.Embed:
    """Easily add fields to an embed through a dictionary of the field names and values."""
    for f_name, f_value in fields.items():
        embed.add_field(name=f_name, value=f_value)
    return embed


async def add_embed_listed_fields(
    embed: disnake.Embed, fields: Dict[str, str]
) -> disnake.Embed:
    """Easily add fields to an embed through a dictionary of the field names and values."""
    for f_name, f_value in fields.items():
        embed.add_field(name=f_name, value=f_value, inline=False)
    return embed


async def create_embeds_from_list(
    items: List[str], groupings: int = 10, title: str = None
) -> List[disnake.Embed]:
    numbered_items = [f"{i + 1}) {items[i]}" for i in range(0, len(items))]
    grouped_items = [
        "\n".join(numbered_items[i : i + groupings])
        for i in range(0, len(numbered_items), groupings)
    ]
    embeds = [
        disnake.Embed(title=title, description=grouped_items[i])
        for i in range(0, len(grouped_items))
    ]
    return embeds