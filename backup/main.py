# main.py

# import pysnooper
import sys
import threading
from pathlib import Path
import random
import sqlite3
import time
from sqlite3 import OperationalError
from typing import Any, Dict, List, Tuple
import cv2
import send2trash
import wx  # _Type: ignore
from runvlc import VLCMediaPlayerGUI
from setup_logger import l, sY, p, sW, sR, sB
from rich.table import Table

# config
# INDIR = Path(r"D:\.projects\test\new")
# OUTDIR = Path(r"D:\.projects\test\Sorted")
INDIR = Path(r"E:\Test")
OUTDIR = Path(r"E:\Test\Q")
DBFILE = Path("config/db.db")
OPTIONSDBFILE = Path("config/options.db")
VALID_EXTENSIONS: list[str] = [".mp4", ".avi", ".mkv"]

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY,
    fileId INTEGER DEFAULT 0,
    Count INTEGER DEFAULT 0,
    destFileName TEXT,
    destFilePath TEXT,
    _Rating INTEGER,
    _Category TEXT,
    _Type TEXT,
    _Tag TEXT,
    FileRes TEXT,
    _Deleted BOOLEAN DEFAULT FALSE,
    _Skipped BOOLEAN DEFAULT FALSE,
    _Processed BOOLEAN DEFAULT FALSE,
    FileSize INTEGER,
    sourceFilePath TEXT,
    soureceFileName TEXT
)
"""

OPTIONSDB_SCHEMA = """
CREATE TABLE IF NOT EXISTS options (
    id INTEGER PRIMARY KEY,
    _Category TEXT UNIQUE,
    _Tag TEXT UNIQUE,
    _Type TEXT UNIQUE
)
"""

CONFIG: Dict[str, Any] = {
    "input_folder": INDIR,
    "output_folder": OUTDIR,
    "database_file": DBFILE,
    "schema": {"media": DB_SCHEMA, },
    "valid_extensions": VALID_EXTENSIONS, }

ALTER_STATEMENTS: list[str] = [
    "ALTER TABLE media ADD COLUMN fileId INTEGER DEFAULT 0",
    "ALTER TABLE media ADD COLUMN Count INTEGER DEFAULT 0",
    "ALTER TABLE media ADD COLUMN destFileName TEXT",
    "ALTER TABLE media ADD COLUMN destFilePath TEXT",
    "ALTER TABLE media ADD COLUMN _Rating INTEGER",
    "ALTER TABLE media ADD COLUMN _Category TEXT",
    "ALTER TABLE media ADD COLUMN _Type TEXT",
    "ALTER TABLE media ADD COLUMN _Tag TEXT",
    "ALTER TABLE media ADD COLUMN FileRes TEXT",
    "ALTER TABLE media ADD COLUMN _Deleted BOOLEAN DEFAULT FALSE",
    "ALTER TABLE media ADD COLUMN _Skipped BOOLEAN DEFAULT FALSE",
    "ALTER TABLE media ADD COLUMN _Processed BOOLEAN DEFAULT FALSE",
    "ALTER TABLE media ADD COLUMN FileSize INTEGER",
    "ALTER TABLE media ADD COLUMN sourceFilePath TEXT",
    "ALTER TABLE media ADD COLUMN soureceFileName TEXT",
]

ALTER_OPTION_STATEMENTS: list[str] = [
    "ALTER TABLE media ADD COLUMN _Category TEXT UNIQUE",
    "ALTER TABLE media ADD COLUMN _Type TEXT UNIQUE",
    "ALTER TABLE media ADD COLUMN _Tag TEXT UNIQUE",
]


def checkDB(db_file) -> None:
    db_path = Path(db_file)
    if not db_path.exists():
        l.error(msg=f"Database file {db_file} not found. Creating a new database.")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()


checkDB(db_file=CONFIG["database_file"])
checkDB(db_file=OPTIONSDBFILE)


def ZZZ() -> None:  # sleepy sleepy time
    time.sleep(random.randint(a=1, b=2))


class ErrorLogger:
    def __init__(self) -> None:
        pass

    def handle_error(self, error: Exception) -> None:
        """Handles and logs different _Types of errors."""
        if isinstance(error, OperationalError):
            self.log_operational_error(error__Type="Operational Error", error=error, style=sR)  # Handling OperationalError
        if isinstance(error, sqlite3.ProgrammingError) and "Error binding parameter" in str(error):
            self.log_exception(error__Type="Programming Error", error=error, style=sR)  # Handling ProgrammingError
        elif isinstance(error, sqlite3.Error):
            self.log_exception(error__Type="SQLite Error", error=error, style=sR)  # Handling other SQLite errors
        elif isinstance(error, PermissionError):
            self.log_exception(error__Type="Permission Error", error=error, style=sR)  # Handling PermissionError
        else:
            self.log_exception(error__Type="Exception", error=error, style=sB)  # Handling generic exceptions

    def log_exception(self, error__Type: str, error: Exception, style) -> None:
        """Logs exceptions with rich formatting."""
        l.exception(msg=f"{error__Type} occurred: {error}", exc_info=error)
        p.print(f"{error__Type}: {error}", style=style)
        p.print_exception()

    def log_operational_error(self, error__Type: str, error: OperationalError, style) -> None:
        """Specifically logs OperationalErrors with rich formatting."""
        l.error(msg=f"{error__Type}: {error}")
        p.print(f"{error__Type}: {error}", style=style)
        p.print_exception()


class mediaPlayer:
    """ A class representing a media player.
    Attributes: app (Any): The wx.App instance.
    player_gui (VLCMediaPlayerGUI): The VLCMediaPlayerGUI instance.
    Methods:  __init__(): Initializes the mediaPlayer object.
              play(media_file): Plays the specified media file.
              stop(): Stops the media playback."""

    def __init__(self) -> None:
        self.app: Any = wx.App(False)
        self.player_gui = VLCMediaPlayerGUI(parent=None)

    def play(self, media_file) -> None:
        if hasattr(media_file, 'sourceFilePath'):
            self.player_gui.load_media(filepath=str(object=media_file.sourceFilePath))
            self.player_gui.on_play(event=None)
        else:
            l.error(msg="Media file does not have a 'sourceFilePath' attribute")

    def stop(self) -> None:
        self.player_gui.on_stop(event=None)

    def remove(self) -> None:
        try:
            self.player_gui.on_remove()
        except Exception as e:
            l.error(msg=f"Error during media player removal: {e}")


class MediaDetails:
    """Represents a media file with attributes such as FileRes, FileSize, _Category, _Tag, etc."""

    def __init__(self, filepath) -> None:
        """Initialize a new fMedia object.
        Args: filepath (Path): The filepath of the media file."""
        self.error_logger = ErrorLogger()
        try:
            self.fileId: int = random.randint(1, 999999)
            self.Count = 0
            self.destFileName = None
            self.destFilePath = None
            self._Rating = 0
            self._Category = None
            self._Type = None
            self._Tag = None
            self._Deleted = False
            self._Skipped = False
            self._Processed = False
            self.sourceFilePath: Any = filepath
            self.soureceFileName = filepath.name
            self.FileSize: int = self.getMediaSize()
            self.FileRes: str = self.getMediaFileDetails()
            # l.info(f"MediaDetails initialized for {self.soureceFileName}")
        except Exception as e:
            l.error(f"Error during initialization of MediaDetails: {e}")
            self.error_logger.handle_error(error=e)

    def getMediaQuality(self, FileRes) -> str:
        """ Determine the quality of the media based on FileRes. """
        width, height = map(int, FileRes.split("x"))
        if width >= 3840 and height >= 2160:
            return "4K"
        elif width >= 1920 and height >= 1080:
            return "FHD"
        elif width >= 1280 and height >= 720:
            return "HD"
        elif width >= 720 and height >= 480:
            return "SD"
        else:
            return "LowQuality"

    def getMediaSize(self) -> int:
        # sourcery skip: inline-immediately-returned-variable
        """ Get the size of the media file. """
        try:
            size: int = self.sourceFilePath.stat().st_size
            return size
        except Exception as e:
            l.error(msg="Error in getMediaSize")
            self.error_logger.handle_error(error=e)
            return 0

    def getMediaFileDetails(self) -> str:  # sourcery skip: extract-method
        """ Get the FileRes of the media file. """
        try:
            cap = cv2.VideoCapture(filename=str(object=self.sourceFilePath))
            if not cap.isOpened():
                raise ValueError(f"Failed to open {self.soureceFileName} for FileRes")

            width = int(cap.get(propId=cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(propId=cv2.CAP_PROP_FRAME_HEIGHT))
            FileRes: str = f"{width}x{height}"
            quality: str = self.getMediaQuality(FileRes=FileRes)

            p.print("*" * 50, style="green", end="\n")
            p.print(f" [{sW}]getMediaFileDetails:[/][{sB}] {self.sourceFilePath}[/] | [{sW}]Quality:[/][{sR}] {quality} [/]", end="\n")
            p.print("*" * 50, style="green", end="\n")
            return FileRes
        except Exception as e:
            l.error(msg="Error in getMediaFileDetails")
            self.error_logger.handle_error(error=e)
            return "ErrorIn_getMediaFileDetails"

    def is_valid(self) -> bool:
        """ Check if all required attributes are present and valid. """
        required_attributes: list[str] = ['fileId', '_Type', '_Category', '_Tag', '_Rating', 'sourceFilePath', 'soureceFileName']
        return all(getattr(self, attr, None) not in [None, '', 0] for attr in required_attributes)


class mediaRanker:
    def __init__(self, db_ops) -> None:
        """ Initializes a mediaRanker object. Args: db_ops: The database operations object. """
        self.db_ops: Any = db_ops
        self.error_logger = ErrorLogger()

    def getUserChoices(self, option_type: str, allow_new: bool = True) -> list[str]:
        """ Prompts the user for input and returns a list of choices.
        Args:   option__Type: The type of option (e.g., _Rating, _Category, _Tag, _Type).
                allow_new: A boolean indicating whether new options are allowed.
        Returns: A list of user choices."""

        existing_options: Any = self.db_ops.getOptionsForColumn(option_type)
        while True:
            user_input: str = input(f"Enter choice for {option_type}: ").strip()
            user_choices: list[str] = [option.strip() for option in user_input.split(sep=',') if option.strip()]

            if not user_choices:
                l.error(msg="You cannot enter an empty option. Please try again.")
                continue

            if option_type == "_Rating":
                if not all(choice.isdigit() for choice in user_choices):
                    l.error(msg="Invalid input for _Rating. Please enter integers only.")
                    continue

            elif option_type in {"_Category", "_Tag", "_Type"} and any(
                ',' in choice for choice in user_choices
            ):
                l.error(msg="Invalid input, options should not contain commas")
                continue

            if allow_new:
                for choice in user_choices:
                    if choice not in existing_options:
                        self.updateTableWithNewOption(column=option_type, option=choice)
            break
        return user_choices

    def updateTableWithNewOption(self, column: str, option: str) -> None:
        """ Update the media table with a new option for the specified column.
        Args:   column: The column to update.
                option: The new option to add."""
        if not option.strip():
            l.info(msg=f"Cannot add an empty option for {column}")
            return
        query: str = f"UPDATE media SET {column} = ? WHERE {column} IS NULL OR {column} = ''"
        success: Any = self.db_ops.executePOSTQuery(query, (option,))
        if not success:
            l.error(msg=f"Failed to add new option '{option}' to {column}")


class DatabaseConnection:
    def __init__(self, db_file: str) -> None:
        self.db_file: str = db_file
        self.error_logger = ErrorLogger()

    def getDBConnection(self) -> sqlite3.Connection | None:
        """Establish and return a database connection.
        Returns: sqlite3.Connection | None: The database connection object if successful, None otherwise."""
        try:
            return sqlite3.connect(database=self.db_file)
        except Exception as e:
            l.error(msg="Error connecting to database")
            self.error_logger.handle_error(error=e)
            return None

    def initializeDB(self) -> None:
        """ Initializes the database by creating tables and adding columns to existing records.
        Raises: Exception: If there is an error initializing the database."""
        try:
            conn: sqlite3.Connection | None = self.getDBConnection()
            if conn is None:
                l.error(msg="Failed to initialize database: No connection available")
                return
            with conn:
                self.createTables(conn=conn)
                self.createOptionsTable(conn=conn)

                self.addColumnsToExistingRecords(conn=conn)
        except Exception as e:
            l.error(msg="Error initializing database")
            self.error_logger.handle_error(error=e)

    def createOptionsTable(self, conn: sqlite3.Connection) -> None:
        """Create an options table to store available categories, file tags, and types."""
        try:
            cursor: sqlite3.Cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS options (
                    id INTEGER PRIMARY KEY,
                    _Category TEXT UNIQUE,
                    _Tag TEXT UNIQUE,
                    _Type TEXT UNIQUE
                )
            """)
        except Exception as e:
            l.error(msg="Error creating options table")
            self.error_logger.handle_error(error=e)

    def createTables(self, conn: sqlite3.Connection) -> None:
        """Create database tables based on the schema in the CONFIG.
        Args: conn (sqlite3.Connection): The database connection object."""
        try:
            cursor: sqlite3.Cursor = conn.cursor()
            for schema in CONFIG["schema"].values():
                cursor.execute(schema)
        except Exception as e:
            l.error(msg="Error creating tables")
            self.error_logger.handle_error(error=e)

    def addColumnsToExistingRecords(self, conn: sqlite3.Connection) -> None:
        """Add new columns to existing records in the 'media' table.
        Args: conn (sqlite3.Connection): The database connection object"""
        cursor: sqlite3.Cursor = conn.cursor()
        all_successful = True
        for statement in ALTER_STATEMENTS:
            column_name: str = self.getColumnName(statement=statement)
            try:
                cursor.execute(f"SELECT {column_name} FROM media LIMIT 1")
            except Exception as e:
                l.error(msg="Error In addColumnsToExistingRecords:")
                self.error_logger.handle_error(error=e)
                try:
                    cursor.execute(statement)
                except Exception as e:
                    l.error(msg=f"Error adding column {column_name}")
                    self.error_logger.handle_error(error=e)
                    all_successful = False
        if not all_successful:
            l.error(msg="Not all columns were successfully added")

    def getColumnName(self, statement: str) -> str:
        """Extract the column name from an ALTER TABLE statement.
        Args: statement (str): The ALTER TABLE statement.
        Returns: str: The extracted column name."""
        try:
            return statement.split(sep=" ADD COLUMN ")[1].split()[0]
        except Exception as e:
            l.error(msg="Error extracting column name")
            self.error_logger.handle_error(error=e)
            return ""


class dbManager:
    def __init__(self, db_conn: DatabaseConnection) -> None:
        self.db_conn: DatabaseConnection = db_conn
        self.error_logger = ErrorLogger()

    # def executeGETQuery(self, query: str, params: Tuple = ()) -> List[Tuple]:
    #     try:
    #         conn: sqlite3.Connection | None = self.db_conn.getDBConnection()
    #         if conn is None:
    #             raise ConnectionError("Failed to get database connection")
    #         with conn:
    #             cursor: sqlite3.Cursor = conn.cursor()
    #             # cursor.execute(query, params)
    #             cursor.execute(query, params or ())
    #             return cursor.fetchall()
    #     except Exception as e:
    #         l.error(f"Error executing GET query: {query} with params: {params}")
    #         self.error_logger.handle_error(error=e)
    #         return []
    def executeGETQuery(self, query: str, params: Tuple = ()) -> List[Tuple]:
        try:
            conn: sqlite3.Connection | None = self.db_conn.getDBConnection()
            if conn is None:
                raise ConnectionError("Failed to get database connection")

            with conn:
                cursor = conn.cursor()
                # Convert all parameters to strings
                params = tuple(str(p) for p in params)
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            l.error(msg=f"Error executing GET query: {query} with params: {params}")
            self.error_logger.handle_error(error=e)
            return []

    # def executePOSTQuery(self, query: str, params: Tuple = ()) -> bool:
    #     try:
    #         conn: sqlite3.Connection | None = self.db_conn.getDBConnection()
    #         if conn is None:
    #             raise ConnectionError("Failed to get database connection")
    #         with conn:
    #             cursor: sqlite3.Cursor = conn.cursor()
    #             cursor.execute(query, params)
    #             conn.commit()
    #             l.info(msg=f"Successfully executed POST query: {query} with params: {params}")
    #             return True
    #     except Exception as e:
    #         l.error(msg="Error executing POST query")
    #         self.error_logger.handle_error(error=e)
    #         return False

    def executePOSTQuery(self, query: str, params: Tuple = ()) -> bool:
        try:
            conn: sqlite3.Connection | None = self.db_conn.getDBConnection()
            if conn is None:
                raise ConnectionError("Failed to get database connection")

            cursor: sqlite3.Cursor = conn.cursor()
            cursor.execute(query, params)
            # l.info(msg=f"Successfully executed POST query: {query} with params: {params}")
            conn.commit()

            return True
        except Exception as e:
            l.error(msg="Error executing POST query")
            self.error_logger.handle_error(error=e)
            return False

    def getOptionsForColumn(self, column: str) -> List[str]:
        """Retrieve existing options for a specified column from the media table."""
        try:
            query: str = f"SELECT DISTINCT {column} FROM media"
            results = self.executeGETQuery(query=query)
            return [row[0] for row in results if row[0]]  # Exclude None or empty values
        except Exception as e:
            l.error(msg="Error getOptionsForColumn - Returning empty list:")
            self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions
            return []

    def updateRecord(self, media_file, new_file_location, new_file_name):
        """Update media record in the database."""
        try:
            query = """
                UPDATE media SET
                    destFileName = ?,
                    destFilePath = ?,
                    _Category = ?,
                    _Tag = ?,
                    _Type = ?,
                    _Rating = ?,
                    FileRes = ?,
                    _Processed = ?,
                    FileSize = ?,
                    Count = Count + 1
                WHERE sourceFilePath = ?
            """
            params = (
                new_file_name,
                str(new_file_location),
                media_file._Category,
                media_file._Tag,
                media_file._Type,
                media_file._Rating,
                media_file.FileRes,
                media_file._Processed,
                media_file.FileSize,
                str(media_file.sourceFilePath)
            )

            # query = """UPDATE media SET
            #         fileId=?, sourceFilePath=?, soureceFileName=?, destFileName=?,
            #         destFilePath=?, _Category=?, _Tag=?, _Type=?, _Rating=?, FileRes=?,
            #         FileSize=?, _Deleted=?, _Processed=?, _Skipped=?, Count=Count+1
            #         WHERE sourceFilePath=?"""
            # params: tuple[Any, str, Any, Any, str, Any, Any, Any, Any, Any, Any, Any, Any, Any, str] = (
            #     media_file.fileId, str(object=media_file.sourceFilePath), media_file.soureceFileName,
            #     media_file.destFileName, str(object=media_file.destFilePath) if media_file.destFilePath else '',
            #     media_file._Category, media_file._Tag, media_file._Type, media_file._Rating, media_file.FileRes,
            #     media_file.FileSize, media_file._Deleted, media_file._Processed, media_file._Skipped,
            #     str(object=media_file.sourceFilePath),
            # )

            success = self.executePOSTQuery(query=query, params=params)
            if success:
                # l.info("Record updated successfully.")
                pass
            else:
                l.error("Failed to update the record.")
            return success

            # return self.executePOSTQuery(query=query, params=params)
        except Exception as e:
            l.error(msg="Error updateRecord - Returning False:")
            self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions
            return False

    def insertInitialRecord(self, media_file) -> bool:
        # sourcery skip: extract-method
        try:
            query = """INSERT INTO media (fileId, sourceFilePath, soureceFileName, Count)
                       VALUES (?, ?, ?, ?)"""
            params = (media_file.fileId, str(object=media_file.sourceFilePath), media_file.soureceFileName, 0)
            # l.info(msg=f"Initial records: soureceFileName: {media_file.soureceFileName}")
            # p.print(f"[{sW}]FileId:[/][{sB}] {media_file.fileId}", end="\n")
            # p.print(f"[{sW}]sourceFilePath:[/][{sB}] {media_file.sourceFilePath}", end="\n")
            # p.print(f"[{sW}]Count:[/][{sB}] {media_file.Count}", end="\n")
            return self.executePOSTQuery(query=query, params=params)
        except Exception as e:
            l.error(msg="Error insertInitialRecord - Returning False:")
            self.error_logger.handle_error(error=e)
            return False

    def markFileAsDeleted(self, media_file) -> bool:
        try:
            query = "UPDATE media SET _Deleted = 1 WHERE sourceFilePath = ?"
            return self.executePOSTQuery(query=query, params=(str(object=media_file.sourceFilePath),))
        except Exception as e:
            l.error(msg="Error markFileAsDeleted")
            self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions
            return False

    def increaseViewCount(self, media_file) -> None:
        try:
            query = "UPDATE media SET Count = Count + 1 WHERE sourceFilePath = ?"
            self.executePOSTQuery(query=query, params=(str(object=media_file.sourceFilePath),))
        except Exception as e:
            l.error(msg="Error increaseViewCount")
            self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions

    def verifyUpdate(self, source_file_path):
        try:
            query = "SELECT destFilePath, destFileName FROM media WHERE sourceFilePath = ?"
            result = self.executeGETQuery(query, (source_file_path,))
            l.info(f"Verification result for {source_file_path}: {result}")
        except Exception as e:
            l.error(msg="Error verifying update")
            self.error_logger.handle_error(error=e)

    def updateMediaFilenameAndLocation(self, media_file, new_file_location, new_file_name) -> bool:
        try:
            query = """
                UPDATE media
                SET destFilePath = ?, destFileName = ?
                WHERE sourceFilePath = ?
            """
            # Ensure the paths are properly converted to strings
            new_file_location_str = str(new_file_location)
            source_file_path_str = str(media_file.sourceFilePath)
            params = (new_file_location_str, new_file_name, source_file_path_str)
            # l.info(f"Executing Update: {query} with params {params}")

            result = self.executePOSTQuery(query, params)
            # Add debugging logs
            # l.info(f"Updating media file: {media_file.sourceFilePath}")
            # l.info(f"New file location: {new_file_location}, New file name: {new_file_name}")
            # l.info(f"Update query result: {result}")
            return result
        except Exception as e:
            self.error_logger.handle_error(error=e)
            return False

        #     params = (str(object=new_file_location), new_file_name, str(object=media_file.sourceFilePath))
        #     l.info(f"Updating media file: Query {query} with params: {params}")
        #     result: bool = self.executePOSTQuery(query=query, params=params)

        #     # Add debugging logs
        #     l.info(f"Updating media file: {media_file.sourceFilePath}")
        #     l.info(f"New file location: {new_file_location}, New file name: {new_file_name}")
        #     l.info(f"Update query result: {result}")

        #     return result
        # except Exception as e:
        #     self.error_logger.handle_error(error=e)
        #     return False

    def getQuery_printTable(self, query: str, get_table: str) -> None:
        """Print the database table based on the provided query."""
        if get_table == 'media':
            query = f"{query}{get_table}"
            try:
                l.info(f"Executing query: {query}")
                get_db_data = self.executeGETQuery(query=query)
                # Create a table with specified headers

                table = Table(show_header=True, header_style="bold green")
                table.add_column(header="ID", justify="center")
                table.add_column(header="fileId", justify="center")
                table.add_column(header="Count", justify="center")
                table.add_column(header="destFileName", justify="center")
                table.add_column(header="destFilePath", justify="center")
                table.add_column(header="_Rating", justify="center")
                table.add_column(header="_Category", justify="center")
                table.add_column(header="_Type", justify="center")
                table.add_column(header="_Tag", justify="center")
                table.add_column(header="FileRes", justify="center")
                table.add_column(header="_Deleted", justify="center")
                table.add_column(header="_Skipped", justify="center")
                table.add_column(header="_Processed", justify="center")
                table.add_column(header="FileSize", justify="center")
                table.add_column(header="sourceFilePath", justify="center")
                table.add_column(header="sourceFileName", justify="center")
                for row in get_db_data:
                    file_size = row[13]  # File size is at index 13
                    if file_size is not None:
                        size_mb = file_size / (1024 * 1024)  # Convert to MB
                        size_gb = file_size / (1024 * 1024 * 1024)  # Convert to GB
                        size_display = f"{size_mb:.2f} MB" if size_mb < 1024 else f"{size_gb:.2f} GB"
                    else:
                        size_display = "N/A"

                    row = list(row)  # Convert the row tuple to a list for modification

                    row[13] = size_display  # Update the file size in the row with the formatted size_display

                    table.add_row(*[str(item) for item in row])  # Add the updated row to the table
                p.print(table)
            except Exception as e:
                l.error(msg="Error getQuery_printTable media table")
                self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions

        elif get_table == 'options':
            query = f"{query}{get_table}"
            try:
                l.info(f"Executing query: {query}")
                get_db_data = self.executeGETQuery(query=query)
                table = Table(show_header=True, header_style="bold blue")
                table.add_column(header="ID", justify="center")
                table.add_column(header="_Category", justify="center")
                table.add_column(header="_Type", justify="center")
                table.add_column(header="_Tag", justify="center")
                p.print(table)
            except Exception as e:
                l.error(msg="Error getQuery_printTable options table")
                self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions
        else:
            try:
                query = query
                l.info(f"Executing query: {query}")
                get_db_data = self.executeGETQuery(query=query)
                table = Table(show_header=True, header_style="bold green")
                table.add_column(header="ID", justify="center")
                table.add_column(header="fileId", justify="center")
                table.add_column(header="Count", justify="center")
                table.add_column(header="destFileName", justify="center")
                table.add_column(header="destFilePath", justify="center")
                table.add_column(header="_Rating", justify="center")
                table.add_column(header="_Category", justify="center")
                table.add_column(header="_Type", justify="center")
                table.add_column(header="_Tag", justify="center")
                table.add_column(header="FileRes", justify="center")
                table.add_column(header="_Deleted", justify="center")
                table.add_column(header="_Skipped", justify="center")
                table.add_column(header="_Processed", justify="center")
                table.add_column(header="FileSize", justify="center")
                table.add_column(header="sourceFilePath", justify="center")
                table.add_column(header="sourceFileName", justify="center")
                for row in get_db_data:
                    file_size = row[13]  # File size is at index 13
                    if file_size is not None:
                        size_mb = file_size / (1024 * 1024)  # Convert to MB
                        size_gb = file_size / (1024 * 1024 * 1024)  # Convert to GB
                        size_display = f"{size_mb:.2f} MB" if size_mb < 1024 else f"{size_gb:.2f} GB"
                    else:
                        size_display = "N/A"

                    row = list(row)  # Convert the row tuple to a list for modification

                    row[13] = size_display  # Update the file size in the row with the formatted size_display

                    table.add_row(*[str(item) for item in row])  # Add the updated row to the table
                p.print(table)
            except Exception as e:
                l.error(msg="Error getQuery_printTable media table")
                self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions


class FileProcessor:
    def __init__(self, db_ops, media_ranker, media_player, db_conn) -> None:
        """
        Initialize the class with the given parameters.
        Args:
            db_ops (dbManager): The database operations object.
            media_ranker (Any): The media ranker object.
            media_player (Any): The media player object.
            db_conn (DatabaseConnection): The database connection object.
        """
        self.db_ops: dbManager = db_ops
        self.media_ranker: Any = media_ranker
        self.media_player: Any = media_player
        self.db_connector: DatabaseConnection = db_conn
        self.error_logger = ErrorLogger()

    def check_ifRecordExists(self, filepath) -> bool:
        """ Check if a record exists in the 'media' table with the given source file path.
        Args: filepath (str): The source file path to check.
        Returns: bool: True if a record exists, False otherwise."""
        try:
            query = "SELECT COUNT(*) FROM media WHERE sourceFilePath = ?"
            result = self.db_ops.executeGETQuery(query=query, params=(str(object=filepath),))
            return result is not None and result[0][0] > 0

        except Exception as e:
            l.error(msg="Error check_ifRecordExists - Returning False")
            self.error_logger.handle_error(error=e)
            return False

    def renameAndMoveFile(self, media_file) -> Tuple[Path, str]:
        """ Renames and moves the media file to a new location based on its attributes.
        Args: media_file: The media file object.
        Returns: A tuple containing the new output path and the renamed output file name."""
        # self.media_player.stop()
        # self.media_player.remove(media_file=media_file)
        self.media_player.remove()
        ZZZ()
        output_dir: Any = CONFIG["output_folder"] / media_file._Type / media_file._Category
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file_name: str = f"{media_file._Rating}_{media_file._Tag}_{media_file.soureceFileName}"
        output_path: Any = output_dir / output_file_name

        try:
            media_file.sourceFilePath.rename(output_path)
            media_file._Processed = True
            return output_path, output_file_name
        except Exception as e:
            l.error(msg="Error renameAndMoveFile - Returning empty output path and empty output file name")
            self.error_logger.handle_error(error=e)
            return Path(''), ''

    def processSingleFile(self, file) -> bool:
        # sourcery skip: extract-duplicate-method, extract-method
        """Process the given file by playing it, updating its attributes, and interacting with the user."""
        # l.info(msg="Processing file: " + str(object=file))
        media_file = MediaDetails(filepath=file)
        wx.CallAfter(callableObj=self.media_player.play, media_file=media_file)

        if not self.check_ifRecordExists(filepath=media_file.sourceFilePath):
            self.db_ops.insertInitialRecord(media_file=media_file)

        try:
            user_choices = {
                "_Type": lambda: self.media_ranker.getUserChoices("_Type"),
                "_Category": lambda: self.media_ranker.getUserChoices("_Category"),
                "_Tag": lambda: self.media_ranker.getUserChoices("_Tag"),
                "_Rating": lambda: self.media_ranker.getUserChoices("_Rating")
            }
            for attribute, input_func in user_choices.items():
                user_input = input_func()
                if isinstance(user_input, list):
                    user_input = user_input[0] if user_input else None
                if self.isSpecialCommand(user_input=user_input):
                    return self.handleSpecialCommand(user_input=user_input, media_file=media_file)
                setattr(media_file, attribute, user_input)

            media_file._Rating = int(media_file._Rating) if isinstance(media_file._Rating, str) and media_file._Rating.isdigit() else 0
            media_file._Deleted = False
            media_file._Processed = False
            media_file._Skipped = False
            media_file.Count = 0

            self.media_player.stop()
            ZZZ()

            if not media_file.is_valid():
                l.error(msg="Media file has missing or invalid values. Skipping database operations.")
                return False

            newDestPath, newFileName = self.renameAndMoveFile(media_file=media_file)
            if newDestPath and newFileName:
                update_successful = self.db_ops.updateMediaFilenameAndLocation(
                    media_file=media_file, new_file_location=newDestPath, new_file_name=newFileName)
                self.db_ops.verifyUpdate(str(media_file.sourceFilePath))
                if update_successful:
                    try:
                        self.db_ops.updateRecord(media_file=media_file, new_file_location=newDestPath, new_file_name=newFileName)
                        p.print(f"[{sW}]Moved From:[/][{sY}] {media_file.sourceFilePath}[/]", end="\n")
                        p.print(f"[{sW}]Moved To:[/][{sY}] {newDestPath}[/]", end="\n")
                        typecat: str = f"[{sW}]_Type:[/][{sY}] {media_file._Type}[/] | [{sW}]_Category:[/][{sY}] {media_file._Category}[/]"
                        tagrating: str = f"[{sW}]_Tag:[/][{sY}] {media_file._Tag}[/] | [{sW}]Rank:[/][{sY}] {media_file._Rating}[/]"
                        p.print(f"{typecat} | {tagrating}", end="\n")
                        if self.check_ifRecordExists(filepath=media_file.sourceFilePath):
                            # p.print("Record updated successfully.")
                            pass
                        else:
                            # p.print("Failed to update the record.")
                            pass
                    except Exception as e:
                        l.error(msg="processSingleFile| Error during updateRecord - Returning False")
                        self.error_logger.handle_error(error=e)
                        return False
                    # l.info(msg=f"File processing result: {media_file}")
                    return True
                else:
                    l.error(msg="processSingleFile| Error during updateRecord - Returning False")
                    return False
            else:
                l.error(msg="Failed to move and rename the file")
                return False
        except Exception as e:
            l.error(msg="Error processing single file")
            self.error_logger.handle_error(error=e)
            return False

    def isSpecialCommand(self, user_input) -> bool:
        if isinstance(user_input, str) and user_input.startswith('!'):
            command_without_prefix: str = user_input[1:].lower()
            special_commands: set[str] = {"0", "1", "66", "!D", "!d", "X", "x", "!S", "!s", "!q", "!Q",
                                          "!DELETE", "!DEL", "!del", "!skip", "!SKIP", "!Skip", "!quit", "!QUIT", "!END", "!end"}

            return command_without_prefix in special_commands
        return False

    def handleSpecialCommand(self, user_input, media_file) -> bool:
        if self.isDeleteCommand(user_input=user_input):
            self.db_ops.increaseViewCount(media_file=media_file)
            return self.deleteMediaFile(media_file=media_file)
        if self.isSkipCommand(user_input=user_input):
            media_file._Skipped = True
            self.db_ops.increaseViewCount(media_file=media_file)
            return True
        if self.isQuitCommand(user_input=user_input):
            l.info(msg=f"Quit command received for {media_file.soureceFileName}")
            l.info(msg=f"Current view {media_file.Count}")
            self.db_ops.increaseViewCount(media_file=media_file)
            l.info(msg=f"Updated view count {media_file.Count}")
            self.media_player.stop()
            ZZZ()
            self.gracefulShutdown()
            return False

        else:
            l.info(msg=f"Unknown special command received for {media_file.soureceFileName}")
            self.media_player.stop()
            ZZZ()
        return False

    def gracefulShutdown(self) -> None:
        """Gracefully shutdown the application, make sure DB does not get corrupted."""
        l.info(msg="Gracefully shutting down the application")
        connection: sqlite3.Connection | None = self.db_connector.getDBConnection()
        if connection is not None:
            connection.close()
            l.info(msg="Database connection closed")
        l.info(msg="Application shutdown successfully")
        sys.exit(0)

    def isDeleteCommand(self, user_input) -> bool:
        return user_input in ["0", "D", "del", "X", "DELETE", "DEL"]

    def isSkipCommand(self, user_input) -> bool:
        return user_input in ["1", "s", "skip", "S", "SKIP", "Skip"]

    def isQuitCommand(self, user_input) -> bool:
        return user_input.lower() in ["66", "quit", "q", "end", "QUIT", "Q", "END"]

    def deleteMediaFile(self, media_file) -> bool:
        """Delete the media file and mark it as deleted in the database."""
        try:
            send2trash.send2trash(paths=str(object=media_file.sourceFilePath))
            media_file._Deleted = True
            self.db_ops.markFileAsDeleted(media_file=media_file)
            return True
        except Exception as e:
            l.error(msg="Error deleting media file")
            self.error_logger.handle_error(error=e)
            return False


def processFiles(db_ops, media_ranker, media_player, files, db_conn) -> None:
    try:
        l.info(msg=f"Processing {len(files)} files")
        processor = FileProcessor(db_ops=db_ops, media_ranker=media_ranker, media_player=media_player, db_conn=db_conn)
        while files:
            file = files.pop(0)
            success: bool = processor.processSingleFile(file=file)
            l.info(msg=f"File processing result: {success}")
            l.info(f"File is {file}")
            if not success:
                l.info(msg=f"Failed to process file: {file}")
            try:
                tableName = 'media'
                db_ops.getQuery_printTable(query=f"SELECT * FROM '{tableName}' WHERE sourceFilePath = '{file}'", get_table={tableName})

            except Exception as e:
                l.error(msg=f"Error printing table in processFiles: {e}")
        l.info(msg="All files processed.")
    except Exception as e:
        l.error(msg=f"Error processFiles: {e}")


def startPlayer(db_operations, media_ranker, db_connection) -> None:
    input_folder: Path = CONFIG["input_folder"]
    all_files: list[Path] = [f for f in input_folder.glob(pattern="*") if f.suffix in CONFIG["valid_extensions"] and f.is_file()]
    l.info(msg=f"Found {len(all_files)} files in {input_folder}.")

    if len(all_files) > 0:
        media_player = mediaPlayer()
        random.shuffle(x=all_files)
        app: Any = wx.App(False)
        file_processing_thread = threading.Thread(target=processFiles, args=(
            db_operations, media_ranker, media_player, all_files, db_connection))
        file_processing_thread.start()
        app.MainLoop()
    else:
        l.info(msg="No files to process.")


def main() -> None:
    try:
        db_connection = DatabaseConnection(db_file=CONFIG["database_file"])
        db_operations = dbManager(db_conn=db_connection)
        db_connection.initializeDB()
        db_operations.getQuery_printTable(query="SELECT * FROM ", get_table="media")
        print('\n\n')
        db_operations.getQuery_printTable(query="SELECT * FROM ", get_table="options")
        media_ranker = mediaRanker(db_ops=db_operations)
    except Exception as e:
        p.print(f"Error initializing database and operations: {e}", style="bold red")
        p.print_exception()
        sys.exit(1)
    try:
        startPlayer(db_operations=db_operations, media_ranker=media_ranker, db_connection=db_connection)
    except Exception as e:
        p.print(f"Application terminated due to an unexpected error: {e}", style="bold red")
        p.print_exception()
    finally:
        p.print("\n\nGoodbye...\n")


if __name__ == "__main__":
    main()
