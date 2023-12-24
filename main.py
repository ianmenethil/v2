# main.py
import threading
from pathlib import Path
import random
import sqlite3
import time
from sqlite3 import OperationalError
from typing import Any, Dict, List, Tuple
from typing_extensions import Literal
import cv2
import send2trash
import wx  # type: ignore
from runvlc import VLCMediaPlayerGUI
from setup_logger import l, sY, p, sW, sR
from rich.table import Table


def check_and_create_database(db_file) -> None:
    db_path = Path(db_file)
    if not db_path.exists():
        l.error(msg=f"Database file {db_file} not found. Creating a new database.")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()


# config
INDIR = Path(r"D:\.projects\test\new")
OUTDIR = Path(r"D:\.projects\test\Sorted")
# INDIR = Path(r"E:\OBS_Recordings\New folder")
# OUTDIR = Path(r"E:\OBS_Recordings\New folder")
DBFILE = Path("config/db.db")
VALID_EXTENSIONS: list[str] = [".mp4", ".avi", ".mkv"]
# schema
media = "CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY, fileId INTEGER, original_filepath TEXT, original_filename TEXT, updated_filename TEXT, updated_filepath TEXT, category TEXT, filetag TEXT, type TEXT, ranking INTEGER,resolution TEXT, size INTEGER, is_deleted BOOLEAN DEFAULT FALSE, is_moved BOOLEAN DEFAULT FALSE, is_skipped BOOLEAN DEFAULT FALSE, view_count INTEGER DEFAULT 0)"  # pylint: disable=C0301
CONFIG: Dict[str, Any] = {
    "input_folder": INDIR,
    "output_folder": OUTDIR,
    "database_file": DBFILE,
    "schema": {"media": media, },
    "valid_extensions": VALID_EXTENSIONS, }
check_and_create_database(db_file=CONFIG["database_file"])


class fPlayer:
    def __init__(self) -> None:
        self.app: Any = wx.App(False)
        self.player_gui = VLCMediaPlayerGUI(None)  # Initialize the VLCMediaPlayerGUI

    def play(self, media_file) -> None:
        self.player_gui.load_media(filepath=str(media_file.original_filepath))
        self.player_gui.on_play(event=None)

    def stop(self) -> None:
        self.player_gui.on_stop(event=None)


class fMedia:
    """Represents a media file with attributes such as resolution, size, category, filetag, etc."""

    def __init__(self, filepath) -> None:
        """Initialize a new fMedia object.
        Args: filepath (Path): The filepath of the media file."""
        self.fileId = 0
        self.original_filepath = filepath
        self.original_filename = filepath.name
        self.updated_filename = None
        self.updated_file_location = None
        self.category = None
        self.filetag = None
        self.type = None
        self.ranking = 0
        self.resolution: str = self._get_resolution()
        self.size = self._get_size()
        self.is_deleted = False
        self.is_moved = False
        self.is_skipped = False
        self.view_count = 0

    def calculate_video_quality(self, resolution) -> str:
        width, height = map(int, resolution.split("x"))  # Convert width and height to integers
        if width >= 3840 and height >= 2160:
            return "4K"
        elif width >= 1920 and height >= 1080:
            return "Full HD"
        elif width >= 1280 and height >= 720:
            return "HD"
        elif width >= 720 and height >= 480:
            return "SD"
        else:
            return "Low Quality"

    def _get_size(self) -> Any:
        get_file_size: Any = self.original_filepath.stat().st_size
        return get_file_size

    def _get_resolution(self) -> str:
        """ Get the resolution of the media file.
        Returns: str: The resolution of the media file in the format "widthxheight". """
        try:
            cap = cv2.VideoCapture(filename=str(object=self.original_filepath))
            if cap.isOpened():
                width: float = cap.get(propId=cv2.CAP_PROP_FRAME_WIDTH)
                height: float = cap.get(propId=cv2.CAP_PROP_FRAME_HEIGHT)
                resolution: str = f"{int(width)}x{int(height)}"
                quality: str = self.calculate_video_quality(resolution=resolution)
                p.print("*" * 50, style="green underline", end="\n")
                p.print(f" [{sY}]Processing:[/][{sW}] {self.original_filepath}[/]", style="bold", end="\n")
                p.print(f" [{sY}]Height and Width:[/][{sW}] {height}:{width} [/] ||[{sY}]Quality:[/][{sR}] {quality} [/] ", style="bold", end="\n")
                p.print("*" * 50, style="green underline", end="\n")
                return resolution
            l.error(msg=f"Failed to open {self.original_filename} for resolution")
            return "Unknown"
        except Exception as e:
            l.error(msg=f"Error getting resolution for {self.original_filename}: {e}")
            p.print_exception()
            return "Error"


class fRanker:
    def __init__(self, db_ops) -> None:
        self.db_ops: Any = db_ops

    def get_user_input(self, option_type: str, allow_new: bool = True) -> list[str]:
        """ Prompts the user for input and returns a list of strings.
        Args: option_type (str): The type of option to get input for (e.g., "ranking", "filetag").
              allow_new (bool, optional): Whether to allow the user to enter a new option. Defaults to True.
        Returns: list[str]: A list of strings representing the user's input."""
        existing_options = self.db_ops.get_existing_options(option_type)
        user_choices: List[str] = []
        while True:
            user_input: str = input(f"Enter choice {option_type}: ").strip()
            user_choices = [option.strip() for option in user_input.split(sep=',') if option.strip()]
            if not user_choices:
                l.error(msg="You cannot enter an empty option. Please try again.")
                continue
            if option_type == "ranking":
                try:
                    user_choices = [str(int(choice)) for choice in user_choices]
                except ValueError:
                    l.error(msg="Invalid input for ranking. Please enter integers only.")
                    continue
            elif option_type in ["category", "filetag", "type"]:
                try:
                    user_choices = [choice for choice in user_choices]
                except ValueError:
                    l.error(msg="Invalid input, must be a string")
                    continue
            if allow_new:
                for choice in user_choices:
                    if choice not in existing_options:
                        self.add_new_option(column=option_type, option=choice)
            break
        return user_choices

    def validate_input(self, input_data) -> int:
        ranking = input_data
        if not ranking.isdigit() or int(ranking) < 0:
            raise ValueError("Invalid ranking: Please choose between 1 and 5")
        return int(ranking)

    def update_media_file(self, media_file, input_data) -> None:
        media_file.category = input_data.get("category")
        media_file.filetag = input_data.get("filetag")
        media_file.type = input_data.get("type")
        media_file.ranking = input_data.get("ranking")

    def add_new_option(self, column: str, option: str) -> None:
        """
        Update the media table with a new option for the specified column.
        Args:
            column (str): The column name (e.g., 'type' or 'category').
            option (str): The new option value to add.
        """
        if not option.strip():  # Reject empty strings
            l.info(msg=f"Cannot add an empty option for {column}")
            return
        # Assuming we're adding a new option to a column in all records where it's currently empty
        query: str = f"UPDATE media SET {column} = ? WHERE {column} IS NULL OR {column} = ''"
        success: Any = self.db_ops.execute_non_query(query, (option,))
        if success:
            l.info(msg=f"Added new option '{option}' to {column}")
        else:
            l.error(msg=f"Failed to add new option '{option}' to {column}")


class dbConn:
    def __init__(self, db_file: str) -> None:
        self.db_file: str = db_file

    def get_connection(self) -> Any:
        """Establish and return a database connection."""
        try:
            conn = sqlite3.connect(database=self.db_file)
            return conn
        except sqlite3.Error as e:
            l.error(msg=f"Error connecting to database: {e}")
            return None

    def initialize_database(self) -> None:
        with self.get_connection() as conn:
            self._create_tables(conn=conn)
            self._alter_tables_for_additional_fields(conn=conn)

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        for schema in CONFIG["schema"].values():
            cursor.execute(schema)
        conn.commit()

    def _alter_tables_for_additional_fields(self, conn: sqlite3.Connection) -> None:
        """
        The function `_alter_tables_for_additional_fields` alters a database table by adding multiple
        columns if they do not already exist.

        :param conn: The `conn` parameter is a connection object that represents a connection to a database.
        It is used to execute SQL statements and commit changes to the database
        """
        cursor = conn.cursor()
        alter_statements = [
            "ALTER TABLE media ADD COLUMN fileId INTEGER DEFAULT 0",
            "ALTER TABLE media ADD COLUMN original_filepath TEXT",
            "ALTER TABLE media ADD COLUMN original_filename TEXT",
            "ALTER TABLE media ADD COLUMN updated_filename TEXT",
            "ALTER TABLE media ADD COLUMN updated_filepath TEXT",
            "ALTER TABLE media ADD COLUMN category TEXT",
            "ALTER TABLE media ADD COLUMN filetag TEXT",
            "ALTER TABLE media ADD COLUMN type TEXT",
            "ALTER TABLE media ADD COLUMN ranking INTEGER",
            "ALTER TABLE media ADD COLUMN resolution TEXT",
            "ALTER TABLE media ADD COLUMN size INTEGER",
            "ALTER TABLE media ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE",
            "ALTER TABLE media ADD COLUMN is_moved BOOLEAN DEFAULT FALSE",
            "ALTER TABLE media ADD COLUMN is_skipped BOOLEAN DEFAULT FALSE",
            "ALTER TABLE media ADD COLUMN view_count INTEGER DEFAULT 0",
        ]
        for statement in alter_statements:
            column_name = self.get_column_name(statement=statement)  # Extract the column name from the statement
            try:
                # Check if the column already exists by querying the table for the column
                cursor.execute(f"SELECT {column_name} FROM media LIMIT 1")
                # l.info(msg=f"Column {column_name} already exists, skipping alteration.")
            except OperationalError as e:
                l.error(msg=f"Error during altering table statement: {statement}")
                l.error(msg=f"Error: {e}")
                p.print_exception()
                pass  # Ignore further errors
        conn.commit()

    def get_column_name(self, statement) -> Any | str:
        column_name: str = statement.split(sep="ADD COLUMN")[1].split()[0]
        return column_name


class dbManager:
    def __init__(self, db_conn: dbConn) -> None:
        self.db_conn: dbConn = db_conn

    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Execute a SQL query and return the results."""
        try:
            conn: Any = self.db_conn.get_connection()
            if conn is not None:
                try:
                    with conn:
                        cursor: Any = conn.cursor()
                        if conn is not None:
                            try:
                                cursor.execute(query, params)
                            except sqlite3.OperationalError as e:
                                l.error(msg=f"Error executing query: {e}")
                                p.print_exception()
                                return []
                            return cursor.fetchall()
                        else:
                            l.error(msg="Error executing query")
                            p.print_exception()
                            return []
                except sqlite3.Error as e:
                    l.error(msg=f"Error executing query: {e}")
            return []
        except sqlite3.Error as e:
            l.error(msg=f"Error getting existing options: {e}")
            p.print_exception()
            return []
        except Exception as e:
            l.error(msg=f"Error getting existing options: {e}")
            p.print_exception()
            return []

    def execute_non_query(self, query: str, params: Tuple = ()) -> bool:
        """Execute a non-returning SQL query (e.g., INSERT, UPDATE, DELETE)."""
        try:
            conn: Any = self.db_conn.get_connection()
            if conn is not None:
                try:
                    with conn:
                        cursor: Any = conn.cursor()
                        cursor.execute(query, params)
                        # l.info(msg=f"Executing query: {query} with params: {params}")
                        # l.info(msg=f"Returning true if rowcount > 0: {cursor.rowcount > 0}")
                        return True
                except sqlite3.Error as e:
                    l.error(msg=f"Error executing non-query: {e}")
                    return False
            return False
        except sqlite3.Error as e:
            l.error(msg=f"Error getting existing options: {e}")
            p.print_exception()
            return False
        except Exception as e:
            l.error(msg=f"Error getting existing options: {e}")
            p.print_exception()
            return False

    def get_existing_options(self, column: str) -> List[str]:
        """Retrieve existing options for a specified column from the media table."""
        query: str = f"SELECT DISTINCT {column} FROM media"
        results = self.execute_query(query=query)
        return [row[0] for row in results if row[0]]  # Exclude None or empty values

    def add_new_option(self, table: str, option: str) -> bool:
        """Add a new option to a specified table."""
        try:
            if not option:
                l.info(msg=f"Invalid {option}")
                return False
            query: str = f"INSERT INTO {table} (name) VALUES (?)"
            return self.execute_non_query(query=query, params=(option,))
        except sqlite3.Error as e:
            l.error(msg=f"Error getting existing options: {e}")
            p.print_exception()
            return False
        except Exception as e:
            l.error(msg=f"Error getting existing options: {e}")
            p.print_exception()
            return False

    def update_media_record(self, media_file: Any) -> bool:
        """Update media record in the database."""
        try:
            query = """UPDATE media SET
                    fileId=?, original_filepath=?, original_filename=?, updated_filename=?,
                    updated_filepath=?, category=?, filetag=?, type=?, ranking=?, resolution=?,
                    size=?, is_deleted=?, is_moved=?, is_skipped=?, view_count=view_count+1
                    WHERE original_filepath=?"""
            params: tuple[Any, str, Any, Any, str, Any, Any, Any, Any, Any, Any, Any, Any, Any, str] = (
                media_file.fileId, str(object=media_file.original_filepath), media_file.original_filename,
                media_file.updated_filename, str(object=media_file.updated_file_location) if media_file.updated_file_location else '',
                media_file.category, media_file.filetag, media_file.type, media_file.ranking, media_file.resolution,
                media_file.size, media_file.is_deleted, media_file.is_moved, media_file.is_skipped,
                str(object=media_file.original_filepath),
            )
            return self.execute_non_query(query=query, params=params)
        except sqlite3.Error as e:
            l.error(msg=f"Error update_media_record: {e}")
            p.print_exception()
            return False
        except Exception as e:
            l.error(msg=f"Error update_media_record: {e}")
            p.print_exception()
            return False

    def insert_original_fileloc_fileId_count(self, media_file):
        try:
            query = """INSERT INTO media (fileId, original_filepath, original_filename, view_count)
                       VALUES (?, ?, ?, ?)"""
            params = (media_file.fileId, str(media_file.original_filepath), media_file.original_filename, 0)
            return self.execute_non_query(query, params)
        except Exception as e:
            l.error(msg=f"Error inserting media record: {e}")
            p.print_exception()
            return False

    def mark_file_as_deleted(self, media_file) -> None:
        query = "UPDATE media SET is_deleted = 1 WHERE original_filepath = ?"
        self.execute_non_query(query, (str(media_file.original_filepath),))

    def increment_view_count(self, media_file) -> None:
        query = "UPDATE media SET view_count = view_count + 1 WHERE original_filepath = ?"
        self.execute_non_query(query, (str(media_file.original_filepath),))

    def update_file_location_and_name(self, media_file, new_file_location, new_file_name) -> Any:
        try:
            l.info(f"Trying to update file location and name for media file: {media_file}\n"
                   f"New file location: {new_file_location}\nNew file name: {new_file_name}")

            query = """
                UPDATE media
                SET updated_filepath = ?, updated_filename = ?
                WHERE original_filepath = ?
            """
            params = (str(new_file_location), new_file_name, str(media_file.original_filepath))
            self.execute_non_query(query, params)

            # return self.execute_non_query(query=query, params=params)
        except sqlite3.Error as e:
            l.error(msg=f"Error update_file_location_and_name: {e}")
            p.print_exception()
            return False
        except Exception as e:
            l.error(msg=f"Error update_file_location_and_name: {e}")
            p.print_exception()
            return False


class FileProcessor:
    def __init__(self, db_ops, media_ranker, media_player, db_conn) -> None:
        self.db_ops: dbManager = db_ops  # db_ops should be an instance of dbManager
        self.media_ranker: Any = media_ranker
        self.media_player: Any = media_player
        self.db_connector: dbConn = db_conn

    file_id_counter = 0

    @classmethod
    def get_next_file_id(cls) -> int:
        cls.file_id_counter += 1
        return cls.file_id_counter

    def process(self, file) -> bool:
        media_file = fMedia(filepath=file)
        wx.CallAfter(callableObj=self.media_player.play, media_file=media_file)

        if not self.file_exists(media_file.original_filepath):
            self.db_ops.insert_original_fileloc_fileId_count(media_file)

        try:
            # Get user input for tags, ranking, type, and category
            type_input = self.media_ranker.get_user_input(option_type="type")
            category_input = self.media_ranker.get_user_input(option_type="category")
            filetag_input = self.media_ranker.get_user_input(option_type="filetag")
            ranking_input = self.media_ranker.get_user_input(option_type="ranking")

            # Update media file attributes
            media_file.filetag = filetag_input
            media_file.ranking = ranking_input

            media_file.type = type_input[0] if type_input else None
            media_file.category = category_input[0] if category_input else None
            media_file.filetag = filetag_input[0] if filetag_input else None
            media_file.ranking = ranking_input[0] if ranking_input else 0

            l.info(msg=f"Media file type: {media_file.type} | Media file category: {
                   media_file.category} | Media file tags: {media_file.filetag} | Media file ranking: {media_file.ranking}")
            media_file.fileId = FileProcessor.get_next_file_id()
            l.info(msg=f"Media file ID: {media_file.fileId}")
            # Update media file in the database
            try:
                self.db_ops.update_media_record(media_file=media_file)  # Call it on the db_ops instance
                l.info(msg=f"Media file updated in the database: {media_file}")
            except Exception as e:
                l.error(msg=f"Error updating media file in the database: {e}")
                p.print_exception()
                return False

            user_choice: str = input("Press 'S' to skip, any other key to continue: ").upper()
            if user_choice == "D":
                self.media_player.stop()
                send2trash.send2trash(paths=str(object=file))
                media_file.is_deleted = True
                self.db_ops.mark_file_as_deleted(media_file)
            elif user_choice == "S":
                self.media_player.stop()
                media_file.is_skipped = True
                self.db_ops.increment_view_count(media_file)
            else:
                self.media_player.stop()
                # TODO NOTE ! IS BELOW CORRECT INDENTATION? SHOULD IT BE BELOW 'self.media_player.stop()'?
                new_file_location, new_file_name = self._update_file_location(media_file=media_file)
                self.db_ops.update_file_location_and_name(media_file, new_file_location, new_file_name)
        except ValueError as e:
            self.handle_error(error=e)
            return False
        return True

    def file_exists(self, filepath) -> bool:
        query = "SELECT COUNT(*) FROM media WHERE original_filepath = ?"
        result = self.db_ops.execute_query(query, (str(filepath),))
        # l.info(f"Query: {query} | filepath: {filepath} | result: {result}")
        return result is not None and result[0][0] > 0

    def _update_file_location(self, media_file) -> Tuple[Path, str]:
        self.media_player.stop()  # Ensure media player is stopped and file is released
        time.sleep(2)  # Optional: brief pause to ensure file is released
        output_dir: Any = CONFIG["output_folder"] / media_file.type / media_file.category
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file_name: str = f"{media_file.ranking}_{media_file.filetag}_{media_file.original_filename}"
        output_path: Any = output_dir / output_file_name

        try:
            media_file.original_filepath.rename(output_path)  # Use original_filepath
            media_file.is_moved = True
            return output_path, output_file_name
        except PermissionError as e:
            l.error(msg=f"Error during renaming file: {e}")
            return Path(''), ''  # Return None for both output_path and output_file_name in case of error

    def handle_error(self, error) -> None:
        l.exception(msg="Exception occurred")
        l.error(msg=f"Error during file processing: {error}")
        p.print_exception()


def get_name_from_id(db_ops, table, original_filepath):
    l.info(f"Getting name from original_filepath: {original_filepath} in table: {table} and db_ops: {db_ops}")
    try:
        query = f"SELECT name FROM {table} WHERE original_filepath = ?"
        result = db_ops.execute_query(query, (str(original_filepath),))
        l.info(f"\nQuery: {query}\n File:{original_filepath}\nResult: {result}")
        return result
    except Exception as e:
        l.error(msg=f"Error getting name from id: {e}")
        p.print_exception()
        return "Unknown"


def process_files(db_ops, media_ranker, media_player, files, db_conn) -> None:
    processor = FileProcessor(db_ops=db_ops, media_ranker=media_ranker, media_player=media_player, db_conn=db_conn)
    for file in list(files):
        l.info(msg=f"Files Remaining: {len(files)} | Files Processed: {len(files) -
               len(files)} | Progress: {(len(files) - len(files)) / len(files) * 100}%")
        success: bool = processor.process(file=file)
        l.info(msg=f"File processing result: {success}")
        if not success:
            files.remove(file)
            l.info(msg=f"Removed file: {file}")


def main() -> None:
    db_connection = dbConn(db_file=CONFIG["database_file"])
    db_operations = dbManager(db_conn=db_connection)
    db_connection.initialize_database()
    media_ranker = fRanker(db_ops=db_operations)

    get_db_data = db_operations.execute_query(query="SELECT * FROM media")

    # Create a table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", justify="right")
    # table.add_column("FileID", justify="right")
    table.add_column("Original Filepath")
    table.add_column("Original Filename")
    table.add_column("Updated Filename")
    table.add_column("Updated Filepath")
    table.add_column("Category")
    table.add_column("Filetag")
    table.add_column("Type")
    table.add_column("Ranking", justify="right")
    table.add_column("Resolution")
    table.add_column("Size", justify="right")
    table.add_column("Deleted", justify="center")
    table.add_column("Moved", justify="center")
    table.add_column("Skipped", justify="center")
    table.add_column("View Count", justify="right")

    for row in get_db_data:
        file_size = row[11]  # Assuming the file size is in the 11th column

        # Handle cases where file_size might be None
        if file_size is not None:
            size_mb = file_size / (1024 * 1024)  # Convert to MB
            size_gb = file_size / (1024 * 1024 * 1024)  # Convert to GB
            size_display = f"{size_mb:.2f} MB" if size_mb < 1024 else f"{size_gb:.2f} GB"
        else:
            size_display = "N/A"  # Set a default display for None values

        # Add the row to the table, replacing the original size with the formatted size_display
        table.add_row(*[str(item) for item in row[:-1]], size_display)
    p.print(table)
    try:
        media_player = fPlayer()
        input_folder: Path = CONFIG["input_folder"]
        all_files: list[Path] = [f for f in input_folder.glob(pattern="*") if f.suffix in CONFIG["valid_extensions"] and f.is_file()]
        random.shuffle(x=all_files)  # Randomize the order of files
        app: Any = wx.App(False)
        file_processing_thread = threading.Thread(target=process_files, args=(
            db_operations, media_ranker, media_player, all_files, db_connection))
        file_processing_thread.start()
        app.MainLoop()
    except Exception as e:
        p.print(f"Application terminated due to an unexpected error: {e}", style="bold red")
        p.print_exception()
    finally:
        p.print("Application ended")


if __name__ == "__main__":
    main()
