"""
hhh.py  -- File-Based Contact Book (CSV/JSON)
Windows-friendly. Run with:
    python hhh.py --cli
or
    python hhh.py --cli --file "C:\path\to\contacts.json"
"""

import csv
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import sys

DEFAULT_FIELDS = ["id", "name", "phone", "email", "notes"]


class StorageError(Exception):
    pass


class ContactBook:
    def __init__(self, path: Path):
        self.path = path
        self.contacts: List[Dict[str, str]] = []
        self.filetype = self._detect_filetype()
        self._load()

    def _detect_filetype(self) -> str:
        suffix = self.path.suffix.lower()
        if suffix == ".json":
            return "json"
        if suffix == ".csv":
            return "csv"
        # default to json if no extension
        return "json"

    def _load(self):
        if not self.path.exists():
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            print(f"File {self.path} not found; creating a new {self.filetype.upper()} file.")
            self._save()
            return

        try:
            if self.filetype == "json":
                with self.path.open("r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError as e:
                        raise StorageError(f"JSON decode error: {e}")
                    if isinstance(data, list):
                        self.contacts = data
                    else:
                        raise StorageError("JSON root is not a list.")
            else:  # csv
                with self.path.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    self.contacts = []
                    for row in reader:
                        if not row.get("id"):
                            continue
                        normalized = {k: (row.get(k, "") or "") for k in DEFAULT_FIELDS}
                        self.contacts.append(normalized)
        except StorageError as e:
            backup = self.path.with_suffix(self.path.suffix + ".bak")
            try:
                self.path.rename(backup)
                print(f"Warning: storage file was corrupt or unreadable: {e}")
                print(f"Backed up the problematic file to: {backup}")
            except Exception:
                print(f"Warning: failed to backup the corrupt file: {e}")
            self.contacts = []
            self._save()
        except Exception as e:
            raise StorageError(f"Failed to load contacts: {e}")

    def _save(self):
        try:
            if self.filetype == "json":
                with self.path.open("w", encoding="utf-8") as f:
                    json.dump(self.contacts, f, indent=2, ensure_ascii=False)
            else:
                with self.path.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=DEFAULT_FIELDS)
                    writer.writeheader()
                    for c in self.contacts:
                        row = {k: c.get(k, "") for k in DEFAULT_FIELDS}
                        writer.writerow(row)
        except Exception as e:
            raise StorageError(f"Failed to save contacts: {e}")

    def add_contact(self, name: str, phone: str = "", email: str = "", notes: str = "") -> Dict[str, str]:
        new_contact = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "phone": phone.strip(),
            "email": email.strip(),
            "notes": notes.strip(),
        }
        self.contacts.append(new_contact)
        self._save()
        print(f"Added contact: {new_contact['name']} (id: {new_contact['id']})")
        return new_contact

    def list_contacts(self):
        if not self.contacts:
            print("No contacts found.")
            return
        print("-" * 90)
        print(f"{'ID':36} | {'Name':20} | {'Phone':12} | {'Email':18}")
        print("-" * 90)
        for c in self.contacts:
            id_short = c['id'][:36]
            print(f"{id_short:36} | {c.get('name','')[:20]:20} | {c.get('phone','')[:12]:12} | {c.get('email','')[:18]:18}")
        print("-" * 90)
        print(f"Total contacts: {len(self.contacts)}")

    def find_by_id(self, id_: str) -> Optional[Dict[str, str]]:
        for c in self.contacts:
            if c['id'] == id_:
                return c
        return None

    def search(self, query: str) -> List[Dict[str, str]]:
        q = query.strip().lower()
        results = []
        for c in self.contacts:
            if (q in c.get("name", "").lower()
                or q in c.get("phone", "").lower()
                or q in c.get("email", "").lower()
                or q in c.get("notes", "").lower()):
                results.append(c)
        if results:
            print(f"Search results for '{query}': {len(results)} found.")
            for c in results:
                print(self._format_contact(c))
        else:
            print(f"No results for '{query}'.")
        return results

    def _format_contact(self, c: Dict[str, str]) -> str:
        return (
            f"ID: {c['id']}\n"
            f"Name: {c.get('name','')}\n"
            f"Phone: {c.get('phone','')}\n"
            f"Email: {c.get('email','')}\n"
            f"Notes: {c.get('notes','')}\n"
            f"{'-'*40}"
        )

    def update(self, id_: str, **fields) -> bool:
        contact = self.find_by_id(id_)
        if not contact:
            print(f"No contact with id: {id_}")
            return False
        updated = False
        for key in DEFAULT_FIELDS:
            if key == "id":
                continue
            if key in fields and fields[key] is not None:
                newval = str(fields[key]).strip()
                if contact.get(key, "") != newval:
                    contact[key] = newval
                    updated = True
        if updated:
            self._save()
            print(f"Contact {id_} updated.")
        else:
            print("No changes made.")
        return updated

    def delete(self, id_: str) -> bool:
        contact = self.find_by_id(id_)
        if not contact:
            print(f"No contact with id: {id_}")
            return False
        self.contacts = [c for c in self.contacts if c['id'] != id_]
        self._save()
        print(f"Deleted contact {id_} ({contact.get('name','')}).")
        return True


def demo_cli(path: Path):
    cb = ContactBook(path)
    help_text = (
        "Commands:\n"
        "  add <name> [phone] [email] [notes] - add contact\n"
        "  list - list contacts\n"
        "  search <query> - search by name/phone/email/notes\n"
        "  update <id> name=<name> phone=<phone> email=<email> notes=<notes> - update\n"
        "  delete <id> - delete\n"
        "  help - show commands\n"
        "  exit - quit\n"
    )
    print("Contact Book CLI. Type 'help' for commands.")
    while True:
        try:
            raw = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break
        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            print(help_text)
        elif cmd == "exit":
            print("Exiting.")
            break
        elif cmd == "list":
            cb.list_contacts()
        elif cmd == "add":
            if not args:
                print("Usage: add <name> [phone] [email] [notes]")
                continue
            name = args[0]
            phone = args[1] if len(args) > 1 else ""
            email = args[2] if len(args) > 2 else ""
            notes = " ".join(args[3:]) if len(args) > 3 else ""
            cb.add_contact(name, phone, email, notes)
        elif cmd == "search":
            if not args:
                print("Usage: search <query>")
                continue
            q = " ".join(args)
            cb.search(q)
        elif cmd == "update":
            if not args:
                print("Usage: update <id> key=value ...")
                continue
            id_ = args[0]
            kv = {}
            for token in args[1:]:
                if "=" in token:
                    k, v = token.split("=", 1)
                    if k in DEFAULT_FIELDS and k != "id":
                        kv[k] = v
            cb.update(id_, **kv)
        elif cmd == "delete":
            if not args:
                print("Usage: delete <id>")
                continue
            cb.delete(args[0])
        else:
            print("Unknown command. Type 'help' for commands.")


def main():
    script_dir = Path(__file__).parent.resolve()
    parser = argparse.ArgumentParser(description="Simple file-based Contact Book")
    parser.add_argument("--file", "-f", default=str(script_dir / "contacts.json"),
                        help="contacts file (json or csv). Default: contacts.json next to script")
    parser.add_argument("--cli", action="store_true", help="Run the interactive CLI demo")
    args = parser.parse_args()

    target = Path(args.file)
    if args.cli:
        demo_cli(target)
    else:
        cb = ContactBook(target)
        print("Quick demo: listing contacts (use --cli for interactive mode).")
        cb.list_contacts()


if __name__ == "__main__":
    main()
