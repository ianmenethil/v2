import click
import shutil
import re
from pathlib import Path
from rich.console import Console

console = Console()


def sanitize_filename(filename, pattern, replacement):
    """Sanitize the filename using the given regex pattern and replacement character."""
    sanitized = re.sub(pattern, replacement, filename, flags=re.IGNORECASE)
    return sanitized


def get_unique_filename(destination, filename):
    """Generate a unique filename to avoid overwriting existing files."""
    counter = 1
    new_filename = filename
    while (destination / new_filename).exists():
        name, ext = filename.rsplit('.', 1)
        new_filename = f"{name}_{counter}.{ext}"
        counter += 1
    return new_filename


@click.command()
@click.option('--source', '-s', type=click.Path(exists=True, file_okay=False), help='Source directory path.')
@click.option('--destination', '-d', type=click.Path(file_okay=False), help='Destination directory path.')
@click.option('--pattern', '-p', default='*', help='Pattern to match files (e.g., *.txt). Defaults to all files.')
@click.option('--regex', '-r', default=None, help='Regex pattern to sanitize filenames.')
@click.option('--replacement', '-rp', default='', help='Replacement character for sanitized filenames.')
@click.option('--list-files', '-lf', is_flag=True, help='List files in the source directory.')
@click.option('--list-directories', '-ld', is_flag=True, help='List directories in the source directory.')
@click.option('--copy-files-only', is_flag=True, help='Copy only files from source to destination without folders.')
@click.option('--copy-with-structure', is_flag=True, help='Copy files from source to destination preserving the folder structure.')
def move_files(source, destination, pattern, regex, replacement, list_files, list_directories, copy_files_only, copy_with_structure):
    """
    Move, list, or sanitize files and folders based on the provided options.
    """
    source_path = Path(source) if source else None
    destination_path = Path(destination) if destination else None
    if copy_files_only and copy_with_structure:
        console.print("Please choose only one operation at a time: --copy-files-only or --copy-with-structure.", style="red")
        return

    if source and destination:
        # Move files
        console.print(f"Moving files from source: {source_path} to destination: {
                      destination_path} with pattern '{pattern}'", style="yellow")
        moved_count = 0
        error_count = 0

    if copy_files_only and source and destination:
        console.print(f"Copying files from {source_path} to {destination_path} without preserving folder structure.", style="yellow")
        files_to_copy = source_path.rglob(pattern)
        moved_count = 0
        for file_path in files_to_copy:
            if file_path.is_file():
                # Check for duplicates and get a unique filename if needed
                unique_filename = get_unique_filename(destination_path, file_path.name)
                new_destination = destination_path / unique_filename
                shutil.move(str(file_path), str(new_destination))
                console.print(f"Moved from: {file_path}         To: {new_destination}", style="green")
                moved_count += 1
        console.print(f"Total files moved: {moved_count}", style="blue")

    elif copy_with_structure and source and destination:
        console.print(f"Copying files from {source_path} to {destination_path} while preserving folder structure.", style="yellow")
        files_to_copy = source_path.rglob(pattern)
        moved_count = 0
        for file_path in files_to_copy:
            if file_path.is_file():
                relative_path = file_path.relative_to(source_path)
                new_destination = destination_path / relative_path
                new_destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(new_destination))
                console.print(f'Moved from: {file_path}         To: {new_destination}', style="green")
                moved_count += 1
        console.print(f"Total files copied: {moved_count}", style="blue")

        # for file_path in files_to_move:
        #     if file_path.is_file():
        #         relative_path = file_path.relative_to(source_path)
        #         new_destination = destination_path / relative_path
        #         new_destination.parent.mkdir(parents=True, exist_ok=True)

        #         try:
        #             shutil.move(str(file_path), str(new_destination))
        #             console.print(f'Moved from: {file_path} \nTo: {new_destination}', style="green")
        #             moved_count += 1
        #         except Exception as e:
        #             console.print(f'Error moving from: {file_path} \nTo: {new_destination}', style="red")
        #             console.print(f'Error message: {str(e)}', style="red")
        #             error_count += 1

        # console.print(f"Total files moved: {moved_count}", style="blue")
        # if error_count > 0:
        #     console.print(f"Total errors encountered: {error_count}", style="red")

    elif source or destination:
        target_path = source_path if source else destination_path
        if list_files:
            # List files
            console.print("Listing files:", style="magenta")
            files = [f for f in target_path.rglob(pattern) if f.is_file()]
            for file_path in files:
                console.print(f"{file_path}", style="green")
            console.print(f"Total files found: {len(files)}", style="green")

        if list_directories:
            # List directories
            console.print("Listing directories:", style="magenta")
            directories = [d for d in target_path.rglob('*') if d.is_dir()]
            for dir_path in directories:
                console.print(dir_path)
            console.print(f"Total directories found: {len(directories)}", style="green")

        if regex:
            # Sanitize filenames
            console.print(f"Sanitizing filenames at {target_path} with pattern '{regex}'", style="yellow")
            sanitized_count = 0
            files_to_sanitize = target_path.rglob(pattern) if pattern else target_path.rglob('*')
            for file_path in files_to_sanitize:
                if file_path.is_file():
                    original_name = file_path.name
                    sanitized_name = sanitize_filename(original_name, regex, replacement)
                    if sanitized_name != original_name:
                        # Check if the sanitized file already exists and get a unique filename
                        unique_sanitized_name = get_unique_filename(target_path, sanitized_name)
                        new_destination = file_path.with_name(unique_sanitized_name)
                        try:
                            file_path.rename(new_destination)
                            console.print(f"Renamed: {file_path} -> {new_destination}", style="green")
                            sanitized_count += 1
                        except Exception as e:
                            console.print(f"Failed to rename: {file_path} -> {new_destination}", style="red")
                            console.print(f"Error: {e}", style="red")
            console.print(f"Total files sanitized: {sanitized_count}", style="blue")

    else:
        console.print("Please provide --source and --destination to move files, or either one to list or sanitize files.", style="red")


if __name__ == '__main__':
    move_files()
