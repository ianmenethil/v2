# set_logger.py

from rich.style import Style
from rich.traceback import install
from rich.logging import RichHandler
from rich.console import Console
import logging

# Define styles
styles: dict[str, Style] = {
    "sR": Style(color="red", bold=True, italic=True),
    "sB": Style(color="blue", bgcolor="white", underline=True),
    "sG": Style(color="green", reverse=True, blink=True),
    "sY": Style(color="yellow", blink2=True, underline2=True),
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
p = Console()

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
