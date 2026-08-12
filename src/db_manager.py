import sqlite3
import json
import os
import uuid


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate_to_uuid()
        self._migrate_pos_to_list()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS dictionary
                       (
                           id TEXT PRIMARY KEY,
                           conlang TEXT,
                           english TEXT,
                           pos TEXT,
                           description TEXT,
                           tags TEXT,
                           roots TEXT,
                           derived TEXT,
                           ipa TEXT,
                           syllable TEXT,
                           synonyms TEXT,
                           antonyms TEXT
                       )
                       ''')

        cursor.execute('CREATE TABLE IF NOT EXISTS tags (name TEXT PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS parts_of_speech (name TEXT PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS grammar (id INTEGER PRIMARY KEY, rules TEXT, tables TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS presets (name TEXT PRIMARY KEY, main_pattern TEXT, patterns TEXT)')
        self.conn.commit()

    def _migrate_pos_to_list(self):
        """Converts legacy plain-text POS fields into JSON lists."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, pos FROM dictionary")
        rows = cursor.fetchall()

        for row in rows:
            pos_val = row['pos']
            # Check if it exists and is NOT already a JSON list
            if pos_val and not (pos_val.startswith('[') and pos_val.endswith(']')):
                # It's an old plain string; wrap it in a list and convert to JSON
                new_pos = json.dumps([pos_val])
                cursor.execute("UPDATE dictionary SET pos = ? WHERE id = ?", (new_pos, row['id']))
            elif not pos_val:
                # Handle completely empty/null cases safely
                cursor.execute("UPDATE dictionary SET pos = ? WHERE id = ?", (json.dumps([]), row['id']))

        self.conn.commit()

    def _migrate_to_uuid(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(dictionary)")
        columns = [row['name'] for row in cursor.fetchall()]

        if 'id' not in columns:
            print("Migrating dictionary to UUID schema...")
            cursor.execute("ALTER TABLE dictionary RENAME TO old_dictionary")
            self._create_tables()

            cursor.execute("SELECT * FROM old_dictionary")
            old_rows = cursor.fetchall()

            word_map = {}
            migrated_data = []

            # Assign UUIDs and build a lookup map
            for row in old_rows:
                entry = dict(row)
                new_id = str(uuid.uuid4())
                word_map[entry['conlang']] = new_id
                entry['id'] = new_id

                for field in ['english', 'tags', 'roots', 'derived', 'synonyms', 'antonyms']:
                    entry[field] = json.loads(entry[field]) if entry[field] else []
                migrated_data.append(entry)

            # Update string relations to UUID relations
            for entry in migrated_data:
                for field in ['roots', 'derived', 'synonyms', 'antonyms']:
                    entry[field] = [word_map.get(w, w) for w in entry[field] if w in word_map]

            self.save_dictionary(migrated_data)
            cursor.execute("DROP TABLE old_dictionary")
            self.conn.commit()

    def migrate_from_json(self, json_dir):
        """Migrates old JSON files to SQLite and backs them up."""
        dict_file = os.path.join(json_dir, "conlang_dictionary.json")
        tags_file = os.path.join(json_dir, "conlang_tags.json")
        grammar_file = os.path.join(json_dir, "conlang_grammar.json")
        presets_file = os.path.join(json_dir, "generator_presents.json")

        cursor = self.conn.cursor()

        if os.path.exists(dict_file):
            with open(dict_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                word_map = {}
                for entry in data:
                    new_id = str(uuid.uuid4())
                    entry['id'] = new_id
                    word_map[entry.get('conlang', '')] = new_id

                for entry in data:
                    # Update relations mapping strings to UUIDs
                    for field in ['roots', 'derived', 'synonyms', 'antonyms']:
                        entry[field] = [word_map.get(w, w) for w in entry.get(field, []) if w in word_map]

                    cursor.execute('''
                                   INSERT INTO dictionary
                                   (id, conlang, english, pos, description, tags, roots, derived, ipa, syllable,
                                    synonyms, antonyms)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                   ''', (
                                        entry['id'],
                                        entry.get('conlang', ''),
                                        json.dumps(entry.get('english', [])),

                                        # Wrap POS in a list if it's a string, then dump to JSON
                                        json.dumps(entry.get('pos', []) if isinstance(entry.get('pos'), list) else [
                                            entry.get('pos', 'Other')]),

                                        entry.get('description', ''),
                                       json.dumps(entry.get('tags', [])), json.dumps(entry.get('roots', [])),
                                       json.dumps(entry.get('derived', [])), entry.get('ipa', ''),
                                       entry.get('syllable', ''), json.dumps(entry.get('synonyms', [])),
                                       json.dumps(entry.get('antonyms', []))
                                   ))
            os.rename(dict_file, dict_file + ".bak")

        if os.path.exists(tags_file):
            with open(tags_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tags = data if isinstance(data, list) else data.get("tags", [])
                pos_list = data.get("pos", ["Noun", "Verb", "Adjective"]) if isinstance(data, dict) else ["Noun",
                                                                                                          "Verb",
                                                                                                          "Adjective"]

                for t in tags:
                    cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (t,))
                for p in pos_list:
                    cursor.execute('INSERT OR IGNORE INTO parts_of_speech (name) VALUES (?)', (p,))
            os.rename(tags_file, tags_file + ".bak")

        if os.path.exists(grammar_file):
            with open(grammar_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cursor.execute('INSERT OR REPLACE INTO grammar (id, rules, tables) VALUES (1, ?, ?)',
                               (data.get('rules', ''), json.dumps(data.get('tables', {}))))
            os.rename(grammar_file, grammar_file + ".bak")

        if os.path.exists(presets_file):
            with open(presets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for p in data:
                    cursor.execute('INSERT OR IGNORE INTO presets (name, main_pattern, patterns) VALUES (?, ?, ?)',
                                   (p.get('name'), p.get('mainPattern', ''), json.dumps(p.get('patterns', []))))
            os.rename(presets_file, presets_file + ".bak")

        self.conn.commit()

    def get_dictionary(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM dictionary")
        rows = cursor.fetchall()
        dict_list = []
        for row in rows:
            entry = dict(row)
            for field in ['english', 'pos', 'tags', 'roots', 'derived', 'synonyms', 'antonyms']:
                entry[field] = json.loads(entry[field]) if entry[field] else []
            dict_list.append(entry)
        return dict_list

    def save_dictionary(self, dict_data):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM dictionary")
        for entry in dict_data:
            cursor.execute('''
                           INSERT INTO dictionary
                           (id, conlang, english, pos, description, tags, roots, derived, ipa, syllable, synonyms, antonyms)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ''', (
                               entry.get('id', str(uuid.uuid4())),
                               entry['conlang'],
                               json.dumps(entry['english']),
                               json.dumps(entry.get('pos', [])),
                               entry['description'],
                               json.dumps(entry['tags']),
                               json.dumps(entry['roots']),
                               json.dumps(entry['derived']),
                               entry.get('ipa', ''),
                               entry.get('syllable', ''),
                               json.dumps(entry.get('synonyms', [])),
                               json.dumps(entry.get('antonyms', []))
                           ))
        self.conn.commit()

    def get_tags_and_pos(self):
        cursor = self.conn.cursor()
        tags = [row['name'] for row in cursor.execute("SELECT name FROM tags")]
        pos = [row['name'] for row in cursor.execute("SELECT name FROM parts_of_speech")]
        if not pos:
            pos = ["Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction", "Interjection",
                   "Prefix", "Suffix"]
        return tags, pos

    def save_tags_and_pos(self, tags, pos_list):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tags")
        cursor.execute("DELETE FROM parts_of_speech")
        for t in tags:
            cursor.execute('INSERT INTO tags (name) VALUES (?)', (t,))
        for p in pos_list:
            cursor.execute('INSERT INTO parts_of_speech (name) VALUES (?)', (p,))
        self.conn.commit()

    def get_grammar(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT rules, tables FROM grammar WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return {"rules": row['rules'], "tables": json.loads(row['tables'])}
        return {"rules": "", "tables": {}}

    def save_grammar(self, grammar_data):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO grammar (id, rules, tables) VALUES (1, ?, ?)',
                       (grammar_data.get('rules', ''), json.dumps(grammar_data.get('tables', {}))))
        self.conn.commit()

    def get_presets(self):
        cursor = self.conn.cursor()
        presets = []
        for row in cursor.execute("SELECT * FROM presets"):
            presets.append({
                "name": row['name'],
                "mainPattern": row['main_pattern'],
                "patterns": json.loads(row['patterns'])
            })
        return presets

    def save_presets(self, presets):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM presets")
        for p in presets:
            cursor.execute('INSERT INTO presets (name, main_pattern, patterns) VALUES (?, ?, ?)',
                           (p['name'], p['mainPattern'], json.dumps(p['patterns'])))
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
