# set_logger.py

from rich.style import Style
from rich.traceback import install
from rich.logging import RichHandler
from rich.console import Console
import logging

# Define styles
styles: dict[str, Style] = {
    "sR": Style(color="red", italic=True),
    "sB": Style(color="blue", blink=True, underline=True),
    "sY": Style(color="yellow", blink2=True, underline2=True),
    "sG": Style(color="green", reverse=True, blink=True),
    "sM": Style(color="magenta", dim=True, strike=True),
    "sC": Style(color="cyan", encircle=True, overline=True),
    "sW": Style(color="white", bgcolor="black", italic=True, underline=True),
    "sWB": Style(color="white", bgcolor="black", italic=True, underline=True, bold=True),
    "styBlack": Style(color="black", bold=True, frame=True),
    "styHidden": Style(color="red", bgcolor="white", italic=True, conceal=True, underline=True),
}

# Extract style objects
sR, sB, sG, sY, sM, sC, sW, sWB, styBlack, styHidden = styles.values()

# Configure logging
# FORMAT = "%(funcName)s - %(lineno)d|%(asctime)s - %(message)s"
FORMAT = "%(funcName)s | %(message)s"
logging.basicConfig(
    level="INFO",
    style="%",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

l = logging.getLogger(name="rich")  # noqa: E741
install()

### FOLLOWING IS THE CONSOLE CLASS FROM RICH LIBRARY ###
# class Console(
#     *,
#     color_system: Literal['auto', 'standard', '256', 'truecolor', 'windows'] | None = "auto",
#     force_terminal: bool | None = None,
#     force_jupyter: bool | None = None,
#     force_interactive: bool | None = None,
#     soft_wrap: bool = False,
#     theme: Theme | None = None,
#     stderr: bool = False,
#     file: IO[str] | None = None,
#     quiet: bool = False,
#     width: int | None = None,
#     height: int | None = None,
#     style: StyleType | None = None,
#     no_color: bool | None = None,
#     tab_size: int = 8,
#     record: bool = False,
#     markup: bool = True,
#     emoji: bool = True,
#     emoji_variant: EmojiVariant | None = None,
#     highlight: bool = True,
#     log_time: bool = True,
#     log_path: bool = True,
#     log_time_format: str | FormatTimeCallable = "[%X]",
#     highlighter: HighlighterType | None = ReprHighlighter(),
#     legacy_windows: bool | None = None,
#     safe_box: bool = True,
#     get_datetime: (() -> datetime) | None = None,
#     get_time: (() -> float) | None = None,
#     _environ: Mapping[str, str] | None = None
# )
# A high level console interface.

# Args:
#     color_system (str, optional): The color system supported by your terminal,
#         either "standard", "256" or "truecolor". Leave as "auto" to autodetect.
#     force_terminal (Optional[bool], optional): Enable/disable terminal control codes, or None to auto-detect terminal. Defaults to None.
#     force_jupyter (Optional[bool], optional): Enable/disable Jupyter rendering, or None to auto-detect Jupyter. Defaults to None.
#     force_interactive (Optional[bool], optional): Enable/disable interactive mode, or None to auto detect. Defaults to None.
#     soft_wrap (Optional[bool], optional): Set soft wrap default on print method. Defaults to False.
#     theme (Theme, optional): An optional style theme object, or None for default theme.
#     stderr (bool, optional): Use stderr rather than stdout if file is not specified. Defaults to False.
#     file (IO, optional): A file object where the console should write to. Defaults to stdout.
#     quiet (bool, Optional): Boolean to suppress all output. Defaults to False.
#     width (int, optional): The width of the terminal. Leave as default to auto-detect width.
#     height (int, optional): The height of the terminal. Leave as default to auto-detect height.
#     style (StyleType, optional): Style to apply to all output, or None for no style. Defaults to None.
#     no_color (Optional[bool], optional): Enabled no color mode, or None to auto detect. Defaults to None.
#     tab_size (int, optional): Number of spaces used to replace a tab character. Defaults to 8.
#     record (bool, optional): Boolean to enable recording of terminal output,
#         required to call export_html, export_svg, and export_text. Defaults to False.
#     markup (bool, optional): Boolean to enable console_markup. Defaults to True.
#     emoji (bool, optional): Enable emoji code. Defaults to True.
#     emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.
#     highlight (bool, optional): Enable automatic highlighting. Defaults to True.
#     log_time (bool, optional): Boolean to enable logging of time by log methods. Defaults to True.
#     log_path (bool, optional): Boolean to enable the logging of the caller by log. Defaults to True.
#     log_time_format (Union[str, TimeFormatterCallable], optional): If log_time is enabled, either string for strftime or callable that formats the time. Defaults to "[%X] ".
#     highlighter (HighlighterType, optional): Default highlighter.
#     legacy_windows (bool, optional): Enable legacy Windows mode, or None to auto detect. Defaults to None.
#     safe_box (bool, optional): Restrict box options that don't render on legacy Windows.
#     get_datetime (Callable[[], datetime], optional): Callable that gets the current time as a datetime.datetime object (used by Console.log),
#         or None for datetime.now.
#     get_time (Callable[[], time], optional): Callable that gets the current time in seconds, default uses time.monotonic.
p = Console(soft_wrap=True, style=sWB, tab_size=4, record=True, markup=True, emoji=True,
            emoji_variant="emoji", highlight=True, log_time=True, log_path=True, log_time_format="[%X]")

# # Demo how to use each style.
# p.print(f"[{sR}]Red text[/]")
# p.print(f"[{sB}]Blue text[/]")
# p.print(f"[{sG}]Green text[/]")
# p.print(f"[{sY}]Yellow text[/]")
# p.print(f"[{sM}]Magenta text[/]")
# p.print(f"[{sC}]Cyan text[/]")
# p.print(f"[{sW}]White text[/]")
# p.print(f"[{sWB}]White bold text[/]")
# p.print(f"[{styBlack}]Black text[/]")
# p.print(f"[{styHidden}]Hidden text[/]")
