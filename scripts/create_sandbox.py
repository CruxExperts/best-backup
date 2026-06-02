#!/usr/bin/env python3
"""
Sandbox Generation Tool for bbackup Testing

Creates a comprehensive testing sandbox filesystem with diverse file types,
realistic directory structures, and safely harvested system files.
"""

import os
import random
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn


class SandboxGenerator:
    """Generate testing sandbox filesystem."""
    
    def __init__(self, config: Dict[str, Any], console: Console):
        """
        Initialize sandbox generator.
        
        Args:
            config: Configuration dictionary
            console: Rich console for output
        """
        self.config = config
        self.console = console
        self.output_dir = Path(config.get('output', '/tmp/bbackup_sandbox'))
        self.stats = {
            'files_created': 0,
            'dirs_created': 0,
            'total_size': 0,
            'file_types': {},
            'large_files': [],
            'harvested_files': 0,
            'errors': [],
        }
        self.progress = None
    
    def generate(self) -> bool:
        """
        Main generation method.
        
        Returns:
            True if successful
        """
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup progress tracking
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                MofNCompleteColumn(),
                TextColumn("•"),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                self.progress = progress
                
                # Create directory structure
                self.console.print(f"[bold cyan]Creating sandbox: {self.output_dir}[/bold cyan]")
                self.create_structure()
                
                # Generate files
                if self.config.get('structure', {}).get('documents', {}).get('enabled', True):
                    self.generate_text_files()
                    self.generate_code_files()
                    self.generate_markdown_files()
                
                if self.config.get('structure', {}).get('data', {}).get('enabled', True):
                    self.generate_binary_files()
                    self.generate_database_files()
                    self.generate_log_files()
                    self.generate_config_files()
                    self.generate_csv_files()
                
                if self.config.get('structure', {}).get('media', {}).get('enabled', True):
                    self.generate_image_files()
                    if self.config.get('structure', {}).get('media', {}).get('large_files', {}).get('enabled', True):
                        self.generate_large_files()
                
                if self.config.get('structure', {}).get('archives', {}).get('enabled', True):
                    self.generate_archives()
                
                if self.config.get('structure', {}).get('projects', {}).get('enabled', True):
                    self.generate_projects()
                
                if self.config.get('structure', {}).get('temp', {}).get('enabled', True):
                    self.generate_temp_files()
                
                # Harvest system files
                if self.config.get('harvesting', {}).get('enabled', True):
                    self.harvest_system_files()
            
            # Generate final report
            self.generate_report()
            
            self.console.print("\n[bold green]✓ Sandbox created successfully![/bold green]")
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]Error: {e}[/bold red]")
            self.stats['errors'].append(str(e))
            return False
    
    def create_structure(self):
        """Create directory structure."""
        task = self.progress.add_task("Creating directory structure...", total=None)
        
        directories = [
            "archives/old",
            "archives/recent",
            "data/binaries",
            "data/configs",
            "data/databases",
            "data/logs",
            "data/csv_data",
            "data/system_samples",
            "documents/text",
            "documents/code",
            "documents/markdown",
            "media/videos",
            "media/images",
            "media/audio",
            "projects/web/src",
            "projects/web/tests",
            "projects/web/docs",
            "projects/web/config",
            "projects/api/src",
            "projects/api/tests",
            "projects/api/docs",
            "projects/api/config",
            "projects/scripts/src",
            "projects/scripts/tests",
            "projects/scripts/docs",
            "projects/scripts/config",
            "temp/cache",
            "temp/uploads",
            "temp/downloads",
        ]
        
        for dir_path in directories:
            full_path = self.output_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.stats['dirs_created'] += 1
        
        self.progress.update(task, completed=True)
        self.progress.remove_task(task)
    
    def generate_text_files(self):
        """Generate text files."""
        task = self.progress.add_task("Generating text files...", total=4)
        
        text_dir = self.output_dir / "documents/text"
        
        files = [
            ("readme.txt", "This is a README file with important information.\n" * 50),
            ("notes.md", "# Notes\n\n" + "\n".join([f"## Note {i}\nContent for note {i}." for i in range(100)])),
            ("config.json", json.dumps({"app": "test", "version": "1.0", "settings": {"debug": True, "port": 8080}}, indent=2)),
            ("log.txt", "\n".join([f"[2024-01-{i:02d} 12:00:00] INFO: Event {i}" for i in range(1, 1000)])),
        ]
        
        for filename, content in files:
            filepath = text_dir / filename
            filepath.write_text(content)
            self._update_file_stats(filepath)
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_code_files(self):
        """Generate code files."""
        task = self.progress.add_task("Generating code files...", total=4)
        
        code_dir = self.output_dir / "documents/code"
        
        files = {
            "app.py": '''#!/usr/bin/env python3
"""Sample Python application."""
import sys
import json

def main():
    data = {"message": "Hello, World!"}
    print(json.dumps(data))
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
            "app.js": '''// Sample JavaScript application
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.json({ message: 'Hello, World!' });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
''',
            "app.go": '''package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
''',
            "Dockerfile": '''FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked
COPY . .
CMD ["uv", "run", "python", "app.py"]
''',
        }
        
        for filename, content in files.items():
            filepath = code_dir / filename
            filepath.write_text(content)
            self._update_file_stats(filepath)
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_markdown_files(self):
        """Generate markdown documentation files."""
        count = self.config.get('structure', {}).get('documents', {}).get('markdown_count', 200)
        task = self.progress.add_task(f"Generating {count} markdown files...", total=count)
        
        markdown_dir = self.output_dir / "documents/markdown"
        
        for i in range(count):
            filename = markdown_dir / f"doc_{i:04d}.md"
            content = f"# Document {i}\n\n"
            content += f"## Section 1\n\nContent for document {i}, section 1.\n\n"
            content += f"## Section 2\n\nContent for document {i}, section 2.\n\n"
            content += "```python\nprint('Hello, World!')\n```\n" * 10
            filename.write_text(content)
            self._update_file_stats(filename)
            
            if (i + 1) % 20 == 0:
                self.progress.update(task, completed=i + 1)
        
        self.progress.remove_task(task)
    
    def generate_binary_files(self):
        """Generate binary files."""
        count = 20
        task = self.progress.add_task(f"Generating {count} binary files...", total=count)
        
        bin_dir = self.output_dir / "data/binaries"
        
        for i in range(count):
            filename = bin_dir / f"binary_{i:03d}.bin"
            data = os.urandom(random.randint(1024, 10240))
            filename.write_bytes(data)
            self._update_file_stats(filename)
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_database_files(self):
        """Generate database files."""
        task = self.progress.add_task("Generating database files...", total=2)
        
        db_dir = self.output_dir / "data/databases"
        
        # SQL dump
        sql_content = """-- Database dump
CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    created_at TIMESTAMP
);

INSERT INTO users VALUES (1, 'user1', 'user1@example.com', NOW());
INSERT INTO users VALUES (2, 'user2', 'user2@example.com', NOW());
""" * 100
        
        (db_dir / "database.sql").write_text(sql_content)
        self._update_file_stats(db_dir / "database.sql")
        self.progress.advance(task)
        
        # JSON data
        json_data = [{"id": i, "name": f"item_{i}", "value": random.randint(1, 1000)} for i in range(1000)]
        (db_dir / "data.json").write_text(json.dumps(json_data, indent=2))
        self._update_file_stats(db_dir / "data.json")
        self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_log_files(self):
        """Generate log files."""
        task = self.progress.add_task("Generating log files...", total=4)
        
        logs_dir = self.output_dir / "data/logs"
        
        log_types = {
            "app.log": "[INFO] Application started\n" * 5000,
            "error.log": "\n".join([f"[ERROR] {i}: Error message {i}" for i in range(1000)]),
            "access.log": "\n".join([f"127.0.0.1 - - [{i}] \"GET /page{i} HTTP/1.1\" 200 {i*100}" for i in range(2000)]),
            "debug.log": "\n".join([f"[DEBUG] Function call {i}: args={i}, result={i*2}" for i in range(3000)]),
        }
        
        for filename, content in log_types.items():
            filepath = logs_dir / filename
            filepath.write_text(content)
            self._update_file_stats(filepath)
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_config_files(self):
        """Generate configuration files."""
        task = self.progress.add_task("Generating config files...", total=3)
        
        configs_dir = self.output_dir / "data/configs"
        
        configs = {
            "app.yaml": """app:
  name: test-app
  version: 1.0.0
  settings:
    debug: true
    port: 8080
    database:
      host: localhost
      port: 5432
""",
            "nginx.conf": """server {
    listen 80;
    server_name example.com;
    location / {
        proxy_pass http://localhost:8080;
    }
}
""",
            "docker-compose.yml": """version: '3.8'
services:
  app:
    image: python:3.9
    volumes:
      - ./app:/app
""",
        }
        
        for filename, content in configs.items():
            filepath = configs_dir / filename
            filepath.write_text(content)
            self._update_file_stats(filepath)
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_csv_files(self):
        """Generate CSV data files."""
        count = 100
        task = self.progress.add_task(f"Generating {count} CSV files...", total=count)
        
        csv_dir = self.output_dir / "data/csv_data"
        
        for i in range(count):
            filename = csv_dir / f"data_{i:03d}.csv"
            content = "id,name,value\n"
            content += "\n".join([f"{j},{'item_' + str(j)},{random.randint(1,1000)}" for j in range(100)])
            filename.write_text(content)
            self._update_file_stats(filename)
            
            if (i + 1) % 20 == 0:
                self.progress.update(task, completed=i + 1)
        
        self.progress.remove_task(task)
    
    def generate_image_files(self):
        """Generate simulated image files."""
        count = self.config.get('structure', {}).get('media', {}).get('images', {}).get('count', 50)
        task = self.progress.add_task(f"Generating {count} image files...", total=count)
        
        images_dir = self.output_dir / "media/images"
        
        for i in range(count):
            filename = images_dir / f"image_{i:03d}.jpg"
            data = os.urandom(random.randint(50000, 500000))
            filename.write_bytes(data)
            self._update_file_stats(filename)
            
            if (i + 1) % 10 == 0:
                self.progress.update(task, completed=i + 1)
        
        self.progress.remove_task(task)
    
    def generate_large_files(self):
        """Generate large files (videos, archives)."""
        large_config = self.config.get('structure', {}).get('media', {}).get('large_files', {})
        sizes = large_config.get('sizes_mb', [15, 25, 30, 40])
        count = large_config.get('count', 4)
        
        task = self.progress.add_task(f"Generating {count} large files...", total=count)
        
        videos_dir = self.output_dir / "media/videos"
        
        extensions = ['.mp4', '.mkv', '.avi', '.tar.gz']
        
        for i, size_mb in enumerate(sizes[:count]):
            ext = extensions[i % len(extensions)]
            filename = videos_dir / f"video{i+1}{ext}"
            
            # Write in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            size_bytes = size_mb * 1024 * 1024
            
            with open(filename, 'wb') as f:
                remaining = size_bytes
                while remaining > 0:
                    chunk = min(chunk_size, remaining)
                    f.write(os.urandom(chunk))
                    remaining -= chunk
            
            self._update_file_stats(filename)
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def generate_archives(self):
        """Generate archive structure with nested files."""
        archive_config = self.config.get('structure', {}).get('archives', {})
        files_per_month = archive_config.get('files_per_month', 96)
        years = archive_config.get('years', [2020, 2021, 2022, 2023])
        
        total_files = len(years) * 12 * files_per_month * 2  # old + recent
        task = self.progress.add_task("Generating archive files...", total=total_files)
        
        files_created = 0
        
        for archive_type in ["old", "recent"]:
            archive_path = self.output_dir / "archives" / archive_type
            
            for year in years:
                for month in range(1, 13):
                    month_path = archive_path / str(year) / f"{month:02d}"
                    month_path.mkdir(parents=True, exist_ok=True)
                    
                    # Create files per month
                    files_per_day = max(1, files_per_month // 28)
                    for day in range(1, 29):
                        for file_num in range(files_per_day):
                            hour = (file_num * 24) // files_per_day
                            filename = month_path / f"backup_{year}_{month:02d}_{day:02d}_{hour:02d}.txt"
                            content = f"Archive backup from {year}-{month:02d}-{day:02d} {hour:02d}:00\n" * 50
                            filename.write_text(content)
                            self._update_file_stats(filename)
                            files_created += 1
                            
                            if files_created % 100 == 0:
                                self.progress.update(task, completed=files_created)
        
        self.progress.remove_task(task)
    
    def generate_projects(self):
        """Generate project files."""
        project_config = self.config.get('structure', {}).get('projects', {})
        files_per_project = project_config.get('files_per_project', 100)
        project_types = project_config.get('project_types', ['web', 'api', 'scripts'])
        
        total_files = len(project_types) * 4 * files_per_project  # 4 subdirs per project
        task = self.progress.add_task("Generating project files...", total=total_files)
        
        files_created = 0
        
        for project_type in project_types:
            proj_dir = self.output_dir / "projects" / project_type
            
            for subdir in ["src", "tests", "docs", "config"]:
                subdir_path = proj_dir / subdir
                subdir_path.mkdir(parents=True, exist_ok=True)
                
                for i in range(files_per_project):
                    filename = subdir_path / f"file_{i:04d}.txt"
                    content = f"File {i} in {project_type}/{subdir}\n" + "x" * random.randint(100, 1000)
                    filename.write_text(content)
                    self._update_file_stats(filename)
                    files_created += 1
                    
                    if files_created % 50 == 0:
                        self.progress.update(task, completed=files_created)
        
        self.progress.remove_task(task)
    
    def generate_temp_files(self):
        """Generate temporary files."""
        task = self.progress.add_task("Generating temp files...", total=600)
        
        files_created = 0
        
        for subdir in ["cache", "uploads", "downloads"]:
            subdir_path = self.output_dir / "temp" / subdir
            
            for i in range(200):
                filename = subdir_path / f"temp_{i:04d}.tmp"
                content = f"Temporary file {i} in {subdir}\n" + "x" * random.randint(50, 500)
                filename.write_text(content)
                self._update_file_stats(filename)
                files_created += 1
                
                if files_created % 50 == 0:
                    self.progress.update(task, completed=files_created)
        
        self.progress.remove_task(task)
    
    def harvest_system_files(self):
        """Safely harvest files from system."""
        safe_paths = self.config.get('harvesting', {}).get('safe_paths', [
            '/etc/os-release',
            '/etc/hostname',
            '/etc/passwd',
        ])
        max_size_kb = self.config.get('harvesting', {}).get('max_size_kb', 100)
        
        task = self.progress.add_task("Harvesting system files...", total=len(safe_paths))
        
        system_dir = self.output_dir / "data/system_samples"
        
        for src_path in safe_paths:
            if os.path.exists(src_path):
                try:
                    # Check file size
                    size_kb = os.path.getsize(src_path) / 1024
                    if size_kb > max_size_kb:
                        continue
                    
                    # Read and copy (safe, read-only)
                    with open(src_path, 'r', errors='ignore') as f:
                        content = f.read()
                    
                    dst_path = system_dir / os.path.basename(src_path)
                    dst_path.write_text(content)
                    self._update_file_stats(dst_path)
                    self.stats['harvested_files'] += 1
                except Exception as e:
                    self.stats['errors'].append(f"Failed to harvest {src_path}: {e}")
            
            self.progress.advance(task)
        
        self.progress.remove_task(task)
    
    def _update_file_stats(self, filepath: Path):
        """Update statistics for created file."""
        try:
            size = filepath.stat().st_size
            self.stats['files_created'] += 1
            self.stats['total_size'] += size
            
            # Track file types
            ext = filepath.suffix or 'no_ext'
            self.stats['file_types'][ext] = self.stats['file_types'].get(ext, 0) + 1
            
            # Track large files (>1MB)
            if size >= 1024 * 1024:
                self.stats['large_files'].append((str(filepath.relative_to(self.output_dir)), size / (1024 * 1024)))
        except Exception:
            pass
    
    def generate_report(self):
        """Generate final report (README.md)."""
        self.console.print("\n[bold cyan]Generating report...[/bold cyan]")
        
        # Count directories
        total_dirs = sum(1 for _ in self.output_dir.rglob('*') if _.is_dir())
        self.stats['dirs_created'] = total_dirs
        
        # Generate report content
        report = f"""# bbackup Testing Sandbox

**Location:** `{self.output_dir}`  
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Purpose:** Comprehensive testing environment for backup, restore, and delta/incremental backup operations

## Sandbox Statistics

- **Total Files:** {self.stats['files_created']:,} files
- **Total Directories:** {self.stats['dirs_created']:,} directories
- **Total Size:** {self.stats['total_size'] / (1024*1024):.2f} MB ({self.stats['total_size'] / (1024*1024*1024):.2f} GB)
- **File Types:** {len(self.stats['file_types'])} different file types
- **System Files Harvested:** {self.stats['harvested_files']} files

## File Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
"""
        
        # Sort file types by count
        sorted_types = sorted(self.stats['file_types'].items(), key=lambda x: x[1], reverse=True)
        total_files = self.stats['files_created']
        
        for ext, count in sorted_types[:20]:
            percentage = (count / total_files * 100) if total_files > 0 else 0
            report += f"| {ext or 'no_ext'} | {count:,} | {percentage:.1f}% |\n"
        
        if self.stats['large_files']:
            report += "\n## Large Files (>1MB)\n\n"
            for filepath, size_mb in sorted(self.stats['large_files'], key=lambda x: x[1], reverse=True)[:10]:
                report += f"- `{filepath}` - {size_mb:.1f} MB\n"
        
        report += f"""
## Directory Structure

```
{self.output_dir.name}/
├── archives/          # Historical backups
├── data/              # Data files (databases, logs, configs, binaries)
├── documents/         # Documentation (text, code, markdown)
├── media/             # Media files (videos, images, audio)
├── projects/          # Project files (web, api, scripts)
└── temp/              # Temporary files (cache, uploads, downloads)
```

## Testing Scenarios

### 1. Full Backup Test
```bash
# Create Docker volume with sandbox data
docker volume create test_sandbox
docker run --rm -v {self.output_dir}:/source -v test_sandbox:/data alpine sh -c "cp -r /source/* /data/"

# Backup the volume
bbackup backup --volumes-only --containers <container_with_volume>
```

### 2. Incremental Backup Test
```bash
# First backup
bbackup backup --incremental --volumes-only

# Modify some files in sandbox
# ... make changes ...

# Second backup (should only backup changes)
bbackup backup --incremental --volumes-only
```

### 3. Restore Test
```bash
# Restore to new location
bbackup restore --backup-path <backup_path> --volumes test_sandbox
```

### 4. Encryption Test
```bash
# Enable encryption in config
# Backup with encryption
bbackup backup --volumes-only

# Restore encrypted backup
bbackup restore --backup-path <encrypted_backup_path>
```

## Safety Notes

✅ **All system files were safely copied:**
- Read-only access to source files
- Content copied, not moved
- Original files remain untouched
- Only safe, non-sensitive files copied

✅ **Sandbox is isolated:**
- Located in temporary location
- No impact on system files
- Can be safely deleted after testing

## Cleanup

To remove the sandbox:
```bash
rm -rf {self.output_dir}
```

---

**Ready for comprehensive backup/restore/delta testing!** 🚀
"""
        
        # Write report
        report_file = self.output_dir / "README.md"
        report_file.write_text(report)
        
        # Display summary
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold green]SANDBOX GENERATION COMPLETE[/bold green]")
        self.console.print("=" * 70)
        self.console.print(f"\n📍 Location: {self.output_dir}")
        self.console.print(f"📊 Total Files: {self.stats['files_created']:,}")
        self.console.print(f"📁 Total Directories: {self.stats['dirs_created']:,}")
        self.console.print(f"💾 Total Size: {self.stats['total_size'] / (1024*1024):.2f} MB")
        self.console.print(f"🔍 File Types: {len(self.stats['file_types'])}")
        self.console.print(f"📥 System Files Harvested: {self.stats['harvested_files']}")
        
        if self.stats['errors']:
            self.console.print(f"\n⚠️  Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:
                self.console.print(f"   [yellow]{error}[/yellow]")
        
        self.console.print(f"\n📄 Report saved to: {report_file}")
        self.console.print("=" * 70)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults."""
    default_config = {
        'output': '/tmp/bbackup_sandbox',
        'file_count': 13000,
        'total_size_mb': 150,
        'structure': {
            'archives': {
                'enabled': True,
                'files_per_month': 96,
                'years': [2020, 2021, 2022, 2023],
            },
            'projects': {
                'enabled': True,
                'files_per_project': 100,
                'project_types': ['web', 'api', 'scripts'],
            },
            'documents': {
                'enabled': True,
                'markdown_count': 200,
                'code_files': True,
            },
            'media': {
                'enabled': True,
                'large_files': {
                    'enabled': True,
                    'count': 4,
                    'sizes_mb': [15, 25, 30, 40],
                },
                'images': {
                    'enabled': True,
                    'count': 50,
                },
            },
            'data': {
                'enabled': True,
            },
            'temp': {
                'enabled': True,
            },
        },
        'harvesting': {
            'enabled': True,
            'safe_paths': [
                '/etc/os-release',
                '/etc/hostname',
                '/etc/passwd',
            ],
            'max_size_kb': 100,
        },
    }
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f) or {}
            # Merge with defaults
            if 'sandbox' in file_config:
                return _merge_config(default_config, file_config['sandbox'])
            return _merge_config(default_config, file_config)
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
    
    return default_config


def _merge_config(default: Dict, override: Dict) -> Dict:
    """Recursively merge configuration dictionaries."""
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


@click.command()
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='/tmp/bbackup_sandbox',
    help='Output directory for sandbox (default: /tmp/bbackup_sandbox)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='Configuration file path (YAML)'
)
@click.option(
    '--file-count',
    type=int,
    help='Target total file count (overrides config)'
)
@click.option(
    '--size-mb',
    type=int,
    help='Target total size in MB (overrides config)'
)
@click.option(
    '--harvest-system/--no-harvest-system',
    default=True,
    help='Enable/disable system file harvesting (default: enabled)'
)
@click.option(
    '--quick',
    is_flag=True,
    help='Quick mode (fewer files, faster generation)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
def main(output, config, file_count, size_mb, harvest_system, quick, verbose):
    """Generate testing sandbox filesystem for bbackup."""
    console = Console()
    
    # Load configuration
    sandbox_config = load_config(config)
    
    # Override with CLI arguments
    if output:
        sandbox_config['output'] = output
    if file_count:
        sandbox_config['file_count'] = file_count
    if size_mb:
        sandbox_config['total_size_mb'] = size_mb
    if not harvest_system:
        sandbox_config['harvesting']['enabled'] = False
    
    # Apply quick mode
    if quick:
        sandbox_config['structure']['archives']['files_per_month'] = 24
        sandbox_config['structure']['projects']['files_per_project'] = 25
        sandbox_config['structure']['documents']['markdown_count'] = 50
        sandbox_config['structure']['media']['images']['count'] = 10
        sandbox_config['structure']['media']['large_files']['count'] = 2
        sandbox_config['structure']['media']['large_files']['sizes_mb'] = [15, 25]
    
    # Confirm before creating
    console.print("[bold cyan]bbackup Sandbox Generator[/bold cyan]")
    console.print(f"\nOutput directory: [yellow]{sandbox_config['output']}[/yellow]")
    
    if os.path.exists(sandbox_config['output']):
        if not click.confirm("\nDirectory exists. Overwrite?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            return
    
    # Generate sandbox
    generator = SandboxGenerator(sandbox_config, console)
    success = generator.generate()
    
    if success:
        console.print(f"\n[bold green]✓ Sandbox ready at: {sandbox_config['output']}[/bold green]")
    else:
        console.print("\n[bold red]✗ Sandbox generation failed[/bold red]")
        raise click.Abort()


if __name__ == '__main__':
    main()
