# main.py
# import pysnooper
import sys
import threading
from pathlib import Path
import random
import sqlite3
import time
from sqlite3 import OperationalError
from typing import Any, Dict, List, Tuple, Literal, Optional
import cv2
import send2trash
import wx  # _Type: ignore
from runvlc import VLCMediaPlayerGUI
from setup_logger import l, sY, p, sW, sR, sB
from rich.table import Table
import inquirer
import json
import glob

# Load configuration from JSON file
with open(file='config/config.json', mode='r') as config_file:
    CONFIG = json.load(fp=config_file)

INDIR = Path(CONFIG["input_folder"])
OUTDIR = Path(CONFIG["output_folder"])
VALID_EXTENSIONS = CONFIG["valid_extensions"]

MEDIA_dbFile = CONFIG["media_db_file"]
MEDIA_dbSchema = CONFIG["db_schema"]["media"]
MEDIA_dbAlterStatements = CONFIG["alter_statements"]

OPTIONS_dbFile = CONFIG["options_db_file"]
OPTIONS_dbSchema = CONFIG["db_schema"]["options"]
OPTIONS_dbAlter_Statements = CONFIG["alter_option_statements"]




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
    def __init__(self, dbMan) -> None:
        """ Initializes a mediaRanker object. Args: dbMan_ops: The database operations object. """
        self.dbMan_ops: Any = dbMan
        self.error_logger = ErrorLogger()


    def getUserChoices(self, option_type: str, allow_new: bool = True, mediaFile: Optional[str] = None) -> List[str]:
        options: list[str] = self.getOptions(option_type=option_type)
        previous_selection: list[str] = []  # Store the previous selection
        media_file: str = mediaFile if mediaFile is not None else "default_or_fetched_value"
        while True:
            choices: list[str] = options + ["1)New", "2)Back", "3)Skip", "4)Delete", "5)Exit"]
            questions = [inquirer.List(name=option_type, message=f"Select {option_type}", choices=choices)]
            answer: dict[Any, Any] | None = inquirer.prompt(questions=questions)
            if answer is not None:
                selected = answer[option_type]
                if selected == "5)Exit":
                    l.info(msg="User chose to exit... Goodbye")
                    sys.exit()
                if selected == "4)Delete":
                    if option_to_delete := self.prompt_for_option_to_delete(options=options):
                        self.deleteOptionHandling(media_file=media_file)
                        options.remove(option_to_delete)
                elif selected == "3)Skip":
                    self.skipOptionHandling(media_file=media_file)
                elif selected == "2)Back":
                    if previous_selection:
                        return previous_selection  # Go back to the previous level
                    p.print("[sW]You are at the [sB]top[/] level. Cannot go back further.[/]",end="\n",)
                    l.info(msg="")
                elif selected == "1)New" and allow_new:
                    new_option: str = input(f"Enter new {option_type}: ").strip()
                    if new_option and self.validateUserInput(option=new_option):
                        if new_option not in options:
                            # table: Literal['options', 'media'] = "options" if option_type in ['_Category', '_Tag', '_Type'] else "media"
                            table: Literal['options', 'media']  # ! NOTE HERE CHANGE
                            if option_type in {'_Category', '_Tag', '_Type'}:
                                table = "options"
                            elif option_type == '_Rating':
                                table = "media"
                            else:
                                l.error(msg=f"Unknown option type: {option_type}")
                                continue
                            self.updateTableWithNewOption(table_name=table, column=option_type, option=new_option)
                            return [new_option]
                        else:
                            p.print(f"[sW]{new_option} already exists as a {option_type}[/]", end="\n")
                            l.info(msg="Please enter a different one.")
                    else:
                        l.info(msg=f"Invalid {option_type}. Please try again.")
                else:
                    # Update previous selection and break the loop
                    previous_selection = [selected]
                    break
            else:
                l.error(msg="Invalid answer. Please try again.")
                continue
        return previous_selection

    def prompt_for_option_to_delete(self, options):
        questions = [inquirer.List('delete_option', message="Select option to delete", choices=options)]
        answer = inquirer.prompt(questions)
        return answer['delete_option'] if answer else None

    def deleteOptionHandling(self, media_file):
        # Assuming media_file is an object with the necessary attributes, e.g., sourceFilePath
        if self.dbMan_ops.markFileAsDeleted(media_file):
            l.info(msg=f"File marked as deleted: {media_file.sourceFilePath}")
        else:
            l.error(msg=f"Failed to mark file as deleted: {media_file.sourceFilePath}")



    def skipOptionHandling(self, media_file) -> None:
        # Assuming media_file is an object with the necessary attributes, e.g., sourceFilePath
        self.dbMan_ops.increaseViewCount(media_file)
        l.info(msg=f"View count increased for file: {media_file.sourceFilePath}")

    def getOptions(self, option_type: str) -> list[str]:
        if option_type in {'_Category', '_Tag', '_Type'}:
            query: str = f"SELECT DISTINCT {option_type} FROM options"
            results = self.dbMan_ops.executeGETQuery(query=query)
            return [row[0] for row in results if row[0]]  # Exclude None or empty values
        elif option_type == '_Rating':
            return [str(object=i) for i in range(1, 6)]  # Convert integers to strings
            # return list(range(1, 6))  # Return a list of ratings from 1 to 10
        else:
            l.error(msg=f"Unknown option type: {option_type} --> Returning empty list")
            self.error_logger.handle_error(error=Exception(f"Unknown option type: {option_type}"))
            return []

    def validateUserInput(self, option: str) -> bool:
        """Validate the user input option.
        Args: option (str): The user input option to be validated.
        Returns: bool: True if the option is valid, False otherwise.
        """
        option = option.strip()  # Remove leading and trailing whitespace
        if not option:  # Check if the option is empty
            return False
        invalid_chars = set('/:\\')  # Define a set of invalid characters
        return all(char not in invalid_chars for char in option)

    def updateTableWithNewOption(self, table_name: str, column: str, option: str) -> None:
        """Update or insert a new option into the specified table."""
        if not option.strip():
            l.info(msg=f"Cannot add an empty option for {column}")
            return
        if not self.validateUserInput(option=option):
            l.info(msg=f"Cannot add an invalid option for {column}")
            return

        if table_name == "media":
            try:
                media_query: str = f"UPDATE media SET {column} = ? WHERE {column} IS NULL OR {column} = ''"
                media_params: tuple[str] = (option,)
                self.dbMan_ops.executePOSTQuery(media_query, media_params)
            except Exception as e:
                l.error(msg=f"Failed to update {table_name} table with new option '{option}' for {column}: {e}")
                self.error_logger.handle_error(error=e)

        elif table_name == "options":
            try:
                options_query: str = f"INSERT INTO options ({column}) VALUES (?) ON CONFLICT ({column}) DO NOTHING"
                options_params: tuple[str] = (option,)
                self.dbMan_ops.executePOSTQuery(options_query, options_params)
            except Exception as e:
                l.error(msg=f"Failed to update {table_name} table with new option '{option}' for {column}: {e}")
                self.error_logger.handle_error(error=e)

        else:
            l.error(msg=f"Unknown table name: {table_name}")
            return

    def getRating(self) -> int:
        while True:
            try:
                userInput = int(input("Rate the file (1-5): "))
                rating: int = min(5, max(1, userInput))  # Ensures rating is within 1 to 5
                return rating
            except ValueError:
                p.print(f"[{sR}]Invalid rating option: Choose 1 - 5[/]", end="\n")

class Utility:
    @staticmethod
    def checkDB(databaseFile) -> None:
        db_path = Path(databaseFile)
        if not db_path.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_path.touch()

    @staticmethod
    def ZZZ() -> None:
        time.sleep(random.randint(a=1, b=3))

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

    def initializeDB(self) -> None:  # sourcery skip: extract-method
        """ Initializes the database by creating tables and adding columns to existing records.
        Raises: Exception: If there is an error initializing the database."""
        try:
            dbConnection: sqlite3.Connection | None = self.getDBConnection()
            if dbConnection is None:
                l.error(msg="Failed to initialize database: No connection available")
                return
            with dbConnection:
                cursor: sqlite3.Cursor = dbConnection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media'")
                media_result = cursor.fetchone()
                if media_result is None:
                    self.createMediaTable(dbConnection=dbConnection)
                    self.addColumnsToTable(dbConnection=dbConnection)
                else:
                    l.info(msg="Database: media initialized successfully")

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='options'")
                options_results = cursor.fetchone()
                if options_results is None:
                    self.createOptionsTable(dbConnection=dbConnection)
                    self.addColumnsToTable(dbConnection=dbConnection)
                else:
                    l.info("Database: options initialized successfully")

        except Exception as e:
            l.error(msg="Error initializing database")
            self.error_logger.handle_error(error=e)

    def createOptionsTable(self, dbConnection: sqlite3.Connection) -> None:
        """Create an options table to store available categories, file tags, and types."""
        try:
            cursor: sqlite3.Cursor = dbConnection.cursor()
            cursor.execute(OPTIONS_dbSchema)
        except Exception as e:
            l.error(msg="Error creating options table")
            self.error_logger.handle_error(error=e)

    def createMediaTable(self, dbConnection: sqlite3.Connection) -> None:
        """Create database tables based on the schema in the CONFIG."""
        try:
            cursor: sqlite3.Cursor = dbConnection.cursor()
            l.info(msg=f"Creating media table with schema {MEDIA_dbSchema}")
            cursor.execute(MEDIA_dbSchema)
        except Exception as e:
            l.error(msg="Error creating media table")
            self.error_logger.handle_error(error=e)

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

    def addColumnsToTable(self, dbConnection: sqlite3.Connection) -> None:
        cursor: sqlite3.Cursor = dbConnection.cursor()
        all_successful = True
        table = "media"
        for statement in MEDIA_dbAlterStatements:
            try:
                l.info(f"Adding columns to media table {statement}")
                media_column_name: str = self.getColumnName(statement=statement)
            except Exception as e:
                l.error(msg=f"Error In addColumnsToTable MEDIA_dbAlterStatement\n\nStatement was {statement}")
                self.error_logger.handle_error(error=e)
                sys.exit(1)
            try:
                cursor.execute(f"SELECT {media_column_name} FROM media LIMIT 1")
            except Exception as e:
                l.error(msg="Error In addColumnsToTable:")
                self.error_logger.handle_error(error=e)
                try:
                    cursor.execute(statement)
                except Exception as e:
                    l.error(msg=f"Error adding column {media_column_name}")
                    self.error_logger.handle_error(error=e)
                    all_successful = False
        if not all_successful:
            l.error(msg="Not all columns were successfully added")

        table = "options"
        for statement in OPTIONS_dbAlter_Statements:
            try:
                l.info(f"Adding columns to options table {statement}")
                options_column_name: str = self.getColumnName(statement=statement)
            except Exception as e:
                l.error(msg="Error In addColumnsToTable OPTIONS_dbAlter_Statements:")
                self.error_logger.handle_error(error=e)
                continue
            try:
                cursor.execute(f"SELECT {options_column_name} FROM {table} LIMIT 1")
            except Exception as e:
                l.error(msg="Error In addColumnsToTable:")
                self.error_logger.handle_error(error=e)
                try:
                    cursor.execute(statement)
                except Exception as e:
                    l.error(msg=f"Error adding column {options_column_name}")
                    self.error_logger.handle_error(error=e)
                    all_successful = False
        if not all_successful:
            l.error(msg="Not all columns were successfully added")


class DatabaseManager:
    def __init__(self, db_conn: DatabaseConnection) -> None:
        self.db_conn: DatabaseConnection = db_conn
        self.error_logger = ErrorLogger()


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

    def executePOSTQuery(self, query: str, params: Tuple = ()) -> bool:
        # sourcery skip: extract-method
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
                str(object=new_file_location),
                media_file._Category,
                media_file._Tag,
                media_file._Type,
                media_file._Rating,
                media_file.FileRes,
                media_file._Processed,
                media_file.FileSize,
                str(object=media_file.sourceFilePath))

            success: bool = self.executePOSTQuery(query=query, params=params)
            if not success:
                l.error(msg="Failed to update the record.")
            return success
        except Exception as e:
            l.error(msg="Error updateRecord - Returning False:")
            self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions
            return False

    def insertInitialRecord(self, media_file) -> bool:
        # sourcery skip: extract-method
        try:
            query = """INSERT INTO media (fileId, sourceFilePath, soureceFileName, Count) VALUES (?, ?, ?, ?)"""

            # query = """INSERT INTO media (fileId, sourceFilePath, soureceFileName, Count)
            #            VALUES (?, ?, ?, ?)"""

            params = (media_file.fileId, str(object=media_file.sourceFilePath), media_file.soureceFileName, 0)
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
            # l.info(f"Verification result for {source_file_path}: {result}")
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
            new_file_location_str = str(object=new_file_location)
            source_file_path_str = str(object=media_file.sourceFilePath)
            params = (new_file_location_str, new_file_name, source_file_path_str)

            result: bool = self.executePOSTQuery(query=query, params=params)
            return result
        except Exception as e:
            self.error_logger.handle_error(error=e)
            return False

    def getQuery_printTable(self, query: str, tableName: str) -> None:
        """Print the database table based on the provided query."""
        if tableName == 'media':
            query = f"{query}{tableName}"
            try:
                l.info(msg=f"Executing query: {query}")
                getMediaTableData = self.executeGETQuery(query=query)
                mediaTable = Table(show_header=True, header_style="bold green")
                mediaTable.add_column(header="ID", justify="center")
                mediaTable.add_column(header="fileId", justify="center")
                mediaTable.add_column(header="Count", justify="center")
                mediaTable.add_column(header="destFileName", justify="center")
                mediaTable.add_column(header="destFilePath", justify="center")
                mediaTable.add_column(header="_Rating", justify="center")
                mediaTable.add_column(header="_Category", justify="center")
                mediaTable.add_column(header="_Type", justify="center")
                mediaTable.add_column(header="_Tag", justify="center")
                mediaTable.add_column(header="FileRes", justify="center")
                mediaTable.add_column(header="_Deleted", justify="center")
                mediaTable.add_column(header="_Skipped", justify="center")
                mediaTable.add_column(header="_Processed", justify="center")
                mediaTable.add_column(header="FileSize", justify="center")
                mediaTable.add_column(header="sourceFilePath", justify="center")
                mediaTable.add_column(header="sourceFileName", justify="center")
            # ! BURDA BURAYA BAK

                for row in getMediaTableData:
                    row_list = list(row)  # Convert tuple to list

                    # Handle file size formatting
                    file_size = row_list[13]
                    if file_size is not None:
                        size_mb = file_size / (1024 * 1024)
                        size_gb = file_size / (1024 * 1024 * 1024)
                        size_display: str = f"{size_mb:.2f} MB" if size_mb < 1024 else f"{size_gb:.2f} GB"
                    else:
                        size_display = "N/A"
                    row_list[13] = size_display

                    mediaTable.add_row(*[str(item) for item in row_list])  # Add the updated row to the table

                p.print(mediaTable)
            except Exception as e:
                l.error(msg="Error getQuery_printTable media table")
                self.error_logger.handle_error(error=e)


        elif tableName == 'options':
            query = f"{query}{tableName}"
            try:
                l.info(msg=f"Executing query: {query}")
                get_db_data = self.executeGETQuery(query=query)
                optionsTable = Table(show_header=True, header_style="bold blue")
                optionsTable.add_column(header="ID", justify="center")
                optionsTable.add_column(header="_Category", justify="center")
                optionsTable.add_column(header="_Type", justify="center")
                optionsTable.add_column(header="_Tag", justify="center")
                p.print(optionsTable)
            except Exception as e:
                l.error(msg="Error getQuery_printTable options table")
                self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions
        else:
            try:
                get_db_data = self.executeGETQuery(query=query)
                l.info(msg=f"Executing query: {query}")
                l.info(msg=f"Following data found in unknown table: {get_db_data}")
            except Exception as e:
                l.error(msg="Error getQuery_printTable media table")
                self.error_logger.handle_error(error=e)  # Using ErrorLogger to handle exceptions

class FileProcessor:
    def __init__(self, dbMan, media_ranker, media_player, dbConn) -> None:
        """
        Initialize the class with the given parameters.
        Args:
            dbMan_ops (DatabaseManager): The database operations object.
            media_ranker (Any): The media ranker object.
            media_player (Any): The media player object.
            db_conn (DatabaseConnection): The database connection object.
        """
        self.dbMan_ops: DatabaseManager = dbMan
        self.media_ranker: Any = media_ranker
        self.media_player: Any = media_player
        self.db_connector: DatabaseConnection = dbConn
        self.error_logger = ErrorLogger()

    def check_ifRecordExists(self, filepath) -> bool:
        """ Check if a record exists in the 'media' table with the given source file path.
        Args: filepath (str): The source file path to check.
        Returns: bool: True if a record exists, False otherwise."""
        try:
            query = "SELECT COUNT(*) FROM media WHERE sourceFilePath = ?"
            result = self.dbMan_ops.executeGETQuery(query=query, params=(str(object=filepath),))
            return result is not None and result[0][0] > 0

        except Exception as e:
            l.error(msg="Error check_ifRecordExists - Returning False")
            self.error_logger.handle_error(error=e)
            return False

    def renameAndMoveFile(self, media_file, quality) -> Tuple[Path, str]:
        """ Renames and moves the media file to a new location based on its attributes.
        Args: media_file: The media file object.
        Returns: A tuple containing the new output path and the renamed output file name."""
        self.media_player.remove()
        Utility.ZZZ()
        output_dir: Any = OUTDIR / quality / media_file._Type / media_file._Category
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file_name: str = f"{media_file._Tag}_{media_file._Rating}_{media_file.soureceFileName}"
        output_path: Any = output_dir / output_file_name

        try:
            media_file.sourceFilePath.rename(output_path)
            media_file._Processed = True
            return output_path, output_file_name
        except Exception as e:
            l.error(msg="Error renameAndMoveFile - Returning empty output path and empty output file name")
            self.error_logger.handle_error(error=e)
            return Path(''), ''

    def processSingleFile(self, file):
        """Process the given file by playing it, updating its attributes, and interacting with the user."""
        media_file = MediaDetails(filepath=file)
        wx.CallAfter(callableObj=self.media_player.play, media_file=media_file)

        if not self.check_ifRecordExists(filepath=media_file.sourceFilePath):
            self.dbMan_ops.insertInitialRecord(media_file=media_file)

        try:
            user_choices = {
                "_Type": lambda: self.media_ranker.getUserChoices(option_type="_Type", allow_new=True, mediaFile=media_file),
                "_Category": lambda: self.media_ranker.getUserChoices(option_type="_Category", allow_new=True, mediaFile=media_file),
                "_Tag": lambda: self.media_ranker.getUserChoices(option_type="_Tag", allow_new=True, mediaFile=media_file),
            }
            for attribute, input_func in user_choices.items():
                user_input = input_func()
                if isinstance(user_input, list):
                    user_input = user_input[0] if user_input else None
                setattr(media_file, attribute, user_input)

            media_file._Rating = self.media_ranker.getRating()

            media_file._Deleted = False
            media_file._Processed = False
            media_file._Skipped = False
            media_file.Count = 0

            self.media_player.stop()
            Utility.ZZZ()

            if not media_file.is_valid():
                l.error(msg="Media file has missing or invalid values. Skipping database operations.")
                return False

            quality = media_file.FileRes
            qConversion = media_file.getMediaQuality(FileRes=quality)
            l.info(f"Quality Conversion: {qConversion}")
            newDestPath, newFileName = self.renameAndMoveFile(media_file=media_file, quality=qConversion)
            if newDestPath and newFileName:
                update_successful = self.dbMan_ops.updateMediaFilenameAndLocation(
                    media_file=media_file, new_file_location=newDestPath, new_file_name=newFileName)
                self.dbMan_ops.verifyUpdate(str(media_file.sourceFilePath))
                if update_successful:
                    try:
                        self.dbMan_ops.updateRecord(media_file=media_file, new_file_location=newDestPath, new_file_name=newFileName)
                        p.print(f"[{sW}]Moved From:[/][{sY}] {media_file.sourceFilePath}[/]", end="\n")
                        p.print(f"[{sW}]Moved To:[/][{sY}] {newDestPath}[/]", end="\n")
                        typecat: str = f"[{sW}]_Type:[/][{sY}] {media_file._Type}[/] | [{sW}]_Category:[/][{sY}] {media_file._Category}[/]"
                        tagrating: str = f"[{sW}]_Tag:[/][{sY}] {media_file._Tag}[/] | [{sW}]Rank:[/][{sY}] {media_file._Rating}[/]"
                        p.print(f"{typecat} | {tagrating}", end="\n")
                        if self.check_ifRecordExists(filepath=media_file.sourceFilePath):
                            # p.print("Record updated successfully.")
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

    def gracefulShutdown(self) -> None:
        """Gracefully shutdown the application, make sure DB does not get corrupted."""
        l.info(msg="Gracefully shutting down the application")
        connection: sqlite3.Connection | None = self.db_connector.getDBConnection()
        if connection is not None:
            connection.close()
            l.info(msg="Database connection closed")
        l.info(msg="Application shutdown successfully")
        sys.exit(0)

    def deleteMediaFile(self, media_file) -> bool:
        """Delete the media file and mark it as deleted in the database."""
        try:
            send2trash.send2trash(paths=str(object=media_file.sourceFilePath))
            media_file._Deleted = True
            self.dbMan_ops.markFileAsDeleted(media_file=media_file)
            return True
        except Exception as e:
            l.error(msg="Error deleting media file")
            self.error_logger.handle_error(error=e)
            return False


def processFiles(dbMan, media_ranker, media_player, files, dbConn) -> None:
    try:
        l.info(msg=f"Processing {len(files)} files")
        processor = FileProcessor(dbMan=dbMan, media_ranker=media_ranker, media_player=media_player, dbConn=dbConn)
        while files:
            file = files.pop(0)
            success: bool = processor.processSingleFile(file=file)
            if not success:
                l.info(msg=f"Failed to process file: {file}")
            try:
                tableName = 'media'
                dbMan.getQuery_printTable(query=f"SELECT * FROM '{tableName}' WHERE sourceFilePath = '{file}'", tableName={tableName})

            except Exception as e:
                l.error(msg=f"Error printing table in processFiles: {e}")
        l.info(msg="All files processed.")
    except Exception as e:
        l.error(msg=f"Error processFiles: {e}")


def startPlayer(dbMan, media_ranker, dbConn) -> None:
    l.info(msg=f"Starting player in {INDIR}")
    all_files: list[Any] = []
    for extension in VALID_EXTENSIONS:
        all_files.extend(INDIR.glob(pattern=f"*{extension}"))

    l.info(msg=f"Found {len(all_files)} files in {INDIR}.")

    if len(all_files) > 0:
        media_player = mediaPlayer()
        random.shuffle(x=all_files)
        app: Any = wx.App(False)
        file_processing_thread = threading.Thread(target=processFiles, args=(
            dbMan, media_ranker, media_player, all_files, dbConn))
        file_processing_thread.start()
        app.MainLoop()
    else:
        l.info(msg="No files to process.")





def main() -> None:
    errors_file = Path("1.txt")
    if errors_file.exists():
        errors_file.unlink()
    try:
        Utility.checkDB(databaseFile=MEDIA_dbFile)
        Utility.checkDB(databaseFile=OPTIONS_dbFile)
        dbConnector = DatabaseConnection(db_file=MEDIA_dbFile)

        dbConnector.initializeDB()

        dbManager = DatabaseManager(db_conn=dbConnector)

        dbManager.getQuery_printTable(query="SELECT * FROM ", tableName="media")
        print('\n\n')
        dbManager.getQuery_printTable(query="SELECT * FROM ", tableName="options")
        media_ranker = mediaRanker(dbMan=dbManager)
    except Exception as e:
        p.print(f"Error initializing database and operations: {e}", style="bold red")
        p.print_exception()
        sys.exit(1)
    try:
        startPlayer(dbMan=dbManager, media_ranker=media_ranker, dbConn=dbConnector)
    except Exception as e:
        p.print(f"Application terminated due to an unexpected error: {e}", style="bold red")
        p.print_exception()
    finally:
        p.print("\n\nGoodbye...\n")


if __name__ == "__main__":
    main()
