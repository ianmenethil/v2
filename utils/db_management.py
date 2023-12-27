from tkinter import Tk, filedialog
import inquirer
import sqlite3
import yaml
from typing import Any, Dict, List, Literal
from rich.console import Console
from rich.table import Table
console = Console()


class DBConnection:
    def __init__(self, db_file: str):
        self.db_file = db_file

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_file)
        return self.conn

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.close()


def add_column(db_file: str, table_name: str, column_name: str, column_type: str) -> None:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                console.print(f"Column '{column_name}' already exists in table '{table_name}'.")
            else:
                raise e


def insert_record(db_file: str, table_name: str, data: Dict[str, Any]) -> None:
    with DBConnection(db_file) as conn:
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        values = tuple(data.values())
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", values)
        conn.commit()


def execute_custom_query(db_file: str, query: str) -> None:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        records = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        # Create a table
        table = Table(show_header=True, header_style="bold magenta")
        for column in column_names:
            table.add_column(column)

        for row in records:
            # Format each cell as a string to ensure compatibility with the Rich table
            formatted_row = [str(cell) if cell is not None else "N/A" for cell in row]
            table.add_row(*formatted_row)

        console.print(table)


def fetch_all_records(db_file: str, table_name: str) -> list:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        return cursor.fetchall()


def update_record(db_file: str, table_name: str, data: Dict[str, Any], condition: str) -> None:
    with DBConnection(db_file) as conn:
        set_clause = ', '.join([f"{k} = ?" for k in data])
        values = tuple(data.values())
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {condition}", values)
        conn.commit()


def delete_record(db_file: str, table_name: str, condition: str) -> None:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name} WHERE {condition}")
        conn.commit()


def bulk_insert_from_yaml(db_file: str, table_name: str, yaml_file: str) -> None:
    with open(yaml_file, 'r') as file:
        records = yaml.safe_load(file)
        for record in records:
            insert_record(db_file, table_name, record)


def fetch_and_display_records(db_file, table_name) -> list[Any]:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        records = cursor.fetchall()
        # Assuming the first column is the ID
        console.print("\nRecords in the table:")
        for record in records:
            console.print(f"- ID: {record[0]}, Data: {record[1:]}")
        return records


def print_db_records(db_file, table_name) -> None:
    console.print(f"Printint table: {table_name} in database: {db_file}")
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        records = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        # Create a table
        table = Table(show_header=True, header_style="bold magenta")
        for column in column_names:
            table.add_column(column)

        for row in records:
            # Format each cell as a string to ensure compatibility with the Rich table
            formatted_row = [str(cell) if cell is not None else "N/A" for cell in row]
            table.add_row(*formatted_row)

        console.print(table)


# def main_menu() -> Any | Literal['Exit']:
#     questions = [
#         inquirer.List('action',
#                       message="What do you want to do?",
#                       choices=[
#                           'Add Column',
#                           'Insert Record',
#                           'Update Record',
#                           'Delete Record',
#                           'Bulk Insert From YAML',
#                           'Print Records',  # Add this line
#                           'Exit'
#                       ],
#                       ),
#     ]
#     answers = inquirer.prompt(questions)
#     return answers['action'] if answers else 'Exit'

def main_menu() -> Any | Literal['Exit']:
    questions = [
        inquirer.List('action',
                      message="What do you want to do?",
                      choices=[
                          'Add Column',
                          'Insert Record',
                          'Update Record',
                          'Delete Record',
                          'Bulk Insert From YAML',
                          'Print Records',
                          'Execute Custom Query',  # Add this line
                          'Exit'
                      ],
                      ),
    ]
    answers = inquirer.prompt(questions)
    return answers['action'] if answers else 'Exit'


def get_db_file_path() -> Any | str | None:
    questions = [
        inquirer.List('method',
                      message="Choose how to select the database file:",
                      choices=['Enter File Path', 'Browse File'],
                      ),
    ]
    answer = inquirer.prompt(questions)

    if answer['method'] == 'Enter File Path':
        path_question = [
            inquirer.Text('db_file', message="Enter database file path:",
                          validate=lambda _, x: x != '')
        ]
        return inquirer.prompt(path_question)['db_file']
    else:
        root = Tk()
        root.withdraw()  # Hide Tkinter window
        file_path = filedialog.askopenfilename(title="Select Database File", filetypes=[("SQLite files", "*.db")])
        return file_path if file_path else None


def get_table_name(db_file: str) -> Any | None:
    available_tables = get_available_tables(db_file)
    if not available_tables:
        console.print("No tables found in the database.")
        return None

    questions = [
        inquirer.List('method',
                      message="Choose how to select the table:",
                      choices=['Type Table Name', 'Select from List'],
                      ),
    ]
    answer = inquirer.prompt(questions)

    if answer['method'] == 'Type Table Name':
        table_name_question = [
            inquirer.Text('table_name', message="Enter table name:",
                          validate=lambda _, x: x in available_tables or x == '')
        ]
        table_name_answer = inquirer.prompt(table_name_question)
        return table_name_answer['table_name'] if table_name_answer else None
    else:
        table_choice_question = [
            inquirer.List('table_name',
                          message="Choose a table:",
                          choices=available_tables,
                          ),
        ]
        table_choice_answer = inquirer.prompt(table_choice_question)
        return table_choice_answer['table_name'] if table_choice_answer else None


def get_available_tables(db_file: str) -> List[str]:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        return [table[0] for table in tables]


def list_table_columns(db_file, table_name) -> None:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = cursor.fetchall()
        console.print("Columns in the table:")
        for col in columns:
            console.print(f"- {col[1]} (Type: {col[2]})")


def list_column_types(db_file: str, table_name: str) -> Dict[str, str]:
    with DBConnection(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        column_types = {row[1]: row[2] for row in cursor.fetchall()}
    return column_types


def execute_safe_query(db_file, query, params=()) -> bool:
    try:
        with DBConnection(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
    except sqlite3.Error as e:
        console.print(f"An error occurred: {e}")
        return False


def handle_error(e: Exception) -> None:
    if isinstance(e, sqlite3.IntegrityError):
        console.print("Error: Duplicate data or integrity constraint violation.")
    else:
        console.print(f"An error occurred: {e}")


def main() -> None:
    db_file = r"F:\dler\v2\config\media.db"  # Hardcoded database file path

    while True:
        action = main_menu()
        if action == 'Exit':
            break

        # db_file = get_db_file_path()
        # if not db_file:
        #     console.print("No database file selected. Exiting.")
        #     break
        console.print(f"Getting table name from database file: {db_file}")
        table_name = get_table_name(db_file)
        if not table_name:
            console.print("No table name provided or invalid table name. Exiting.")
            break

        if action in ['Add Column', 'Insert Record', 'Update Record', 'Delete Record', 'Bulk Insert From YAML', 'Print Records']:
            list_table_columns(db_file, table_name)

        if action == 'Add Column':
            column_details = inquirer.prompt([
                inquirer.Text('column_name', message="Enter new column name:"),
                inquirer.Text('column_type', message="Enter new column type:")
            ])
            if column_details:
                add_column(db_file, table_name, column_details['column_name'], column_details['column_type'])

        elif action == 'Insert Record':
            data = inquirer.prompt([
                inquirer.Text('data', message='Enter record data as a dictionary (key:value, key:value):')
            ])
            if data:
                try:
                    data_dict = eval(f"dict({data['data']})")
                    insert_record(db_file, table_name, data_dict)
                except SyntaxError:
                    console.print("Invalid data format. Please use the correct dictionary format.")

        # elif action == 'Update Record':
        #     update_data = inquirer.prompt([
        #         inquirer.Text('data', message='Enter new data as a dictionary (key:value, key:value):'),
        #         inquirer.Text('condition', message='Enter condition for update:')
        #     ])
        #     if update_data:
        #         try:
        #             data_dict = eval(f"dict({update_data['data']})")
        #             update_record(db_file, table_name, data_dict, update_data['condition'])
        #         except SyntaxError:
        #             console.print("Invalid data format. Please use the correct dictionary format.")
        elif action == 'Update Record':
            records = fetch_and_display_records(db_file, table_name)
            if not records:
                console.print("No records found to update.")
                continue

            record_id = inquirer.prompt([
                inquirer.Text('record_id', message="Enter the ID of the record to update:")
            ])['record_id']

            # Fetch and display the selected record
            with DBConnection(db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
                selected_record = cursor.fetchone()
                console.print(f"Current data for record ID {record_id}: {selected_record}")

            update_data = inquirer.prompt([
                inquirer.Text('data', message='Enter new data as a dictionary (key:value, key:value):')
            ])

            if update_data:
                try:
                    data_dict = eval(f"dict({update_data['data']})")
                    update_record(db_file, table_name, data_dict, f"id = {record_id}")
                except SyntaxError:
                    console.print("Invalid data format. Please use the correct dictionary format.")

        elif action == 'Execute Custom Query':
            query = inquirer.prompt([
                inquirer.Text('query', message='Enter the SQL query:')
            ])['query']
            if query:
                execute_custom_query(db_file, query)

        elif action == 'Delete Record':
            condition = inquirer.prompt([
                inquirer.Text('condition', message='Enter condition for deletion:')
            ])
            if condition:
                delete_record(db_file, table_name, condition['condition'])

        elif action == 'Bulk Insert From YAML':
            yaml_file = inquirer.prompt([
                inquirer.Text('yaml_file', message='Enter path to YAML file:')
            ])
            if yaml_file:
                bulk_insert_from_yaml(db_file, table_name, yaml_file['yaml_file'])

        elif action == 'Print Records':
            print_db_records(db_file, table_name)


if __name__ == "__main__":
    main()
