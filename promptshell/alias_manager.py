import json
import os
import re
from datetime import datetime
from .setup import CONFIG_DIR
import shlex
from pathlib import Path
from .format_utils import format_text, reset_format

ALIAS_FILE = os.path.join(CONFIG_DIR, "aliases.json")

class AliasManager:
    def __init__(self):
        self.aliases = {}
        self.blacklist = ["rm -rf /", "chmod -R 777 /", ":(){:|:&};:", "mkfs", "dd if=/dev/random"]
        self.load_aliases()
    
    def load_aliases(self):
        if os.path.exists(ALIAS_FILE):
            try:
                with open(ALIAS_FILE, 'r') as f:
                    data = json.load(f)
                    self.aliases = data.get('aliases', {})
            except (json.JSONDecodeError, IOError):
                self.aliases = {}
    
    def save_aliases(self):
        with open(ALIAS_FILE, 'w') as f:
            json.dump({'aliases': self.aliases}, f, indent=2)
    
    def validate_alias_name(self, name):
        return re.match(r'^[a-zA-Z_]\w*$', name) is not None
    
    def validate_command(self, command):
        for dangerous in self.blacklist:
            if dangerous in command:
                return False
        return True
    
    def add_alias(self, name, command, description=""):
        if not self.validate_alias_name(name):
            return False, f"{format_text("red")}Invalid alias name: Name must be alphanumeric with underscores{reset_format()}"
        
        if not self.validate_command(command):
            return False, f"{format_text("red", bold=True)}Invalid Command: Contains dangerous patterns{reset_format()}"
        
        if name in self.aliases:
            return False, f"{format_text("red")}Duplicate alias name: Alias already exists{reset_format()}"
        
        self.aliases[name] = {
            'command': command,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        self.save_aliases()
        return True, f"Alias '{name}' added"
    
    def remove_alias(self, name):
        if name not in self.aliases:
            return False, f"{format_text("red")}Alias not found{reset_format()}"
        
        del self.aliases[name]
        self.save_aliases()
        return True, f"Alias '{name}' removed"
    
    def list_aliases(self, name=None):
        if name:
            return self.aliases.get(name, None)
        return self.aliases
    
    

    def import_aliases(self, file_path):
        file_path = os.path.expanduser(file_path)  # Handles ~
        path_obj = Path(file_path)

        if not path_obj.exists() or not path_obj.is_file():
            return False, f"{format_text("red")}Import error: File '{file_path}' not found.{reset_format()}"

        try:
            with open(path_obj, 'r') as f:
                data = json.load(f)
                for name, alias_data in data.get('aliases', {}).items():
                    if self.validate_alias_name(name) and self.validate_command(alias_data.get('command', '')):
                        self.aliases[name] = alias_data
            self.save_aliases()
            return True, "Aliases imported successfully"
        except json.JSONDecodeError:
            return False, f"{format_text("red")}Invalid JSON: Incorrect JSON format in alias file{reset_format()}."
        except Exception as e:
            return False, f"{format_text("red")}Import error: Failed to import aliases: {str(e)}{reset_format()}"

    
    
    def export_aliases(self, file_path):
        try:
            with open(file_path, 'w') as f:
                json.dump({'aliases': self.aliases}, f, indent=2)
            return True, "Aliases exported successfully"
        except Exception as e:
            return False, f"{format_text("red")}Export failed: {str(e)}{reset_format()}"
    
    def expand_alias(self, input_command):
        parts = input_command.strip().split(maxsplit=1)
        if not parts:
            return input_command
        
        alias_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        if alias_name in self.aliases:
            base_command = self.aliases[alias_name]['command']
            return f"{base_command} {args}".strip()
        return input_command

def handle_alias_command(command: str, alias_manager: AliasManager) -> str:
    try:
        parts = shlex.split(command)
        if len(parts) < 2:
            return f"{format_text("white", bold=True)}Usage: alias [add|remove|list|import|export|help]{reset_format()}"
        
        subcommand = parts[1].lower()
        
        if subcommand == "add" and len(parts) >= 4:
            name = parts[2]
            cmd = " ".join(parts[3:])
            _, message = alias_manager.add_alias(name, cmd)
            return message
        
        elif subcommand == "remove" and len(parts) >= 3:
            _, message = alias_manager.remove_alias(parts[2])
            return message
        
        elif subcommand == "list":
            if len(parts) >= 3:
                alias = alias_manager.list_aliases(parts[2])
                if alias:
                    return f"{parts[2]}: {alias['command']}\nDescription: {alias.get('description', '')}"
                return f"{format_text("red")}Invalid alias name: Alias not found{reset_format()}"
            aliases = alias_manager.list_aliases()
            return "\n".join([f"{name}: {data['command']}" for name, data in aliases.items()])
        
        elif subcommand == "import" and len(parts) >= 3:
            _, message = alias_manager.import_aliases(parts[2])
            return message
        
        elif subcommand == "export" and len(parts) >= 3:
            _, message = alias_manager.export_aliases(parts[2])
            return message
        
        elif subcommand == "help":
            return (
                "Alias Management Commands:\n"
                "  alias add <name> \"<command>\" - Add new alias\n"
                "  alias remove <name> - Remove alias\n"
                "  alias list [name] - List all aliases or show details\n"
                "  alias import <file> - Import aliases from JSON file\n"
                "  alias export <file> - Export aliases to JSON file\n"
                "  alias help - Show this help"
            )
        
        return f"{format_text("red")}Invalid alias command: Use alias help for valid all commands{reset_format()}"
    except Exception as e:
        return f"{format_text("red")}Error processing alias command: {str(e)}{reset_format()}"