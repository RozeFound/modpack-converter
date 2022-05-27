from argparse import ArgumentParser
from importlib import import_module
from pathlib import Path

from aiohttp import TCPConnector
from aiohttp_client_cache.backends.filesystem import FileBackend
from aiohttp_client_cache.session import CachedSession
from jsonpickle import encode as encode_json

from .Helpers.resourceAPI import ResourceAPI
from .Helpers.utils import read_config
from .parser import Parser


async def run():

    formats = ('packwiz', 'Modrinth', 'CurseForge', 'Intermediate')
    providers = ('GitHub', 'CurseForge', 'Modrinth')

    modrinth_search_help = """How accurate modrith search will be:\n
                              exact - uses hash to find file (default)\n
                              accurate - uses mod id, will find more mods without risks\n
                              loose - uses mod name, will find most mods, but have chance to find wrong one"""
 
    arg_parser = ArgumentParser(description="Export MMC modpack to other modpack formats", exit_on_error=True)
    arg_parser.add_argument('-c', '--config', dest='config', type=Path, help='Path to config, used to fill the gaps in parsed data')
    arg_parser.add_argument('-i', '--input', dest='input', type=Path, help='Path to pack', required=True)
    arg_parser.add_argument('-f', '--format', dest='formats', type=str, nargs="+", choices=formats, help='Format to convert to', required=True)
    arg_parser.add_argument('-o', '--output', dest='output', type=Path, help='Specify output directory (optional)', default=Path.cwd())
    arg_parser.add_argument('--modrinth-search', dest='modrinth_search', type=str, choices=('exact', 'accurate', 'loose'), help=modrinth_search_help, default='exact')
    arg_parser.add_argument('--exclude-providers', dest='excluded_providers', type=str, nargs="+", choices=providers, help='List of providers you which to exclude from search', default=str())
    arg_parser.add_argument('--exclude-forbidden', dest='ignore_CF_flag', action='store_false', help='Exclude mods which not allowed for distribution from CurseForge search (disabled by default)')
    args = arg_parser.parse_args()

    if not args.input.exists(): exit("Invalid input!")

    ResourceAPI.modrinth_search_type = args.modrinth_search
    ResourceAPI.excluded_providers = args.excluded_providers
    ResourceAPI.ignore_CF_flag = args.ignore_CF_flag

    cache = FileBackend("mmc-export", use_temp=True, allowed_methods=("GET", "POST", "HEAD"))
    async with CachedSession(cache=cache, connector=TCPConnector(limit=0)) as session: 

        parser = Parser(args.input, session) # type: ignore
        intermediate = await parser.parse()
        read_config(args.config, intermediate)

        for format in args.formats:

            if format == "Intermediate":
                with open(args.output / "intermediate_output.json", "w") as file:
                    file.write(encode_json(intermediate, indent=4, unpicklable=False))
                continue

            module = import_module(f".Formats.{format.lower()}", "mmc_export")
            Writer = getattr(module, format)

            writer = Writer(args.output, intermediate)
            writer.write()         

    return 0

def main():
    import asyncio
    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore
                
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
