#!/usr/bin/env python3

import sys
import argparse
import yaml
import requests
import json
from pathlib import Path
from tabulate import tabulate

sys.path.append(str(Path(__file__).parent.parent.parent))
from pi_client.app.config import ConfigManager


class LabelberryCLI:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.api_url = "http://localhost:8000"
    
    def config_get(self, key: str = None):
        config_dict = self.config.model_dump()
        
        if key:
            if key in config_dict:
                print(f"{key}: {config_dict[key]}")
            else:
                print(f"Error: Key '{key}' not found in configuration")
                sys.exit(1)
        else:
            for k, v in config_dict.items():
                print(f"{k}: {v}")
    
    def config_set(self, key: str, value: str):
        if self.config_manager.update_config(key, value):
            print(f"Successfully updated {key} = {value}")
            print("Note: Restart the service for changes to take effect")
        else:
            print(f"Error: Failed to update configuration key '{key}'")
            sys.exit(1)
    
    def status(self):
        try:
            response = requests.get(f"{self.api_url}/status", timeout=5)
            response.raise_for_status()
            data = response.json()['data']
            
            print("\n=== Labelberry Status ===\n")
            print(f"Device ID: {data['device_id']}")
            print(f"Friendly Name: {data['friendly_name']}")
            print(f"WebSocket Connected: {data['websocket_connected']}")
            
            print("\n--- Printer Status ---")
            printer = data['printer']
            print(f"Connected: {printer['connected']}")
            print(f"Device: {printer['device_path']}")
            print(f"Type: {printer['type']}")
            
            print("\n--- Queue Status ---")
            queue = data['queue']
            print(f"Queue Size: {queue['queue_size']}/{queue['max_size']}")
            print(f"Processing: {queue['processing']}")
            print(f"Current Job: {queue['current_job'] or 'None'}")
            print(f"Pending Jobs: {queue['jobs_pending']}")
            print(f"Failed Jobs: {queue['jobs_failed']}")
            
            print("\n--- System Info ---")
            system = data['system']
            print(f"Hostname: {system.get('hostname', 'Unknown')}")
            print(f"Platform: {system.get('platform', 'Unknown')}")
            print(f"CPU Count: {system.get('cpu_count', 'Unknown')}")
            print(f"Disk Usage: {system.get('disk_usage', 'Unknown')}%")
            
        except requests.RequestException as e:
            print(f"Error: Could not connect to Labelberry service: {e}")
            print("Make sure the service is running: sudo systemctl status labelberry-client")
            sys.exit(1)
    
    def test_print(self):
        try:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            response = requests.post(
                f"{self.api_url}/test-print",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result['success']:
                print("Test print sent successfully!")
            else:
                print(f"Test print failed: {result['message']}")
                
        except requests.RequestException as e:
            print(f"Error: Could not send test print: {e}")
            sys.exit(1)
    
    def queue_list(self):
        try:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            response = requests.get(
                f"{self.api_url}/queue",
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()['data']
            
            if not data['jobs']:
                print("Queue is empty")
                return
            
            print(f"\n=== Print Queue ({data['total']} jobs) ===\n")
            
            table_data = []
            for job in data['jobs']:
                table_data.append([
                    job['id'][:8],
                    job['status'],
                    job['created_at'][:19],
                    job.get('retry_count', 0)
                ])
            
            headers = ["Job ID", "Status", "Created", "Retries"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
        except requests.RequestException as e:
            print(f"Error: Could not retrieve queue: {e}")
            sys.exit(1)
    
    def queue_clear(self):
        response = input("Are you sure you want to clear the print queue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            
            response = requests.get(f"{self.api_url}/queue", headers=headers)
            response.raise_for_status()
            jobs = response.json()['data']['jobs']
            
            cleared = 0
            for job in jobs:
                try:
                    response = requests.delete(
                        f"{self.api_url}/queue/{job['id']}",
                        headers=headers
                    )
                    if response.status_code == 200:
                        cleared += 1
                except:
                    pass
            
            print(f"Cleared {cleared} jobs from queue")
            
        except requests.RequestException as e:
            print(f"Error: Could not clear queue: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Labelberry CLI - Manage your Labelberry Pi client"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_subparsers = config_parser.add_subparsers(dest='config_command')
    
    config_get = config_subparsers.add_parser('get', help='Get configuration value')
    config_get.add_argument('key', nargs='?', help='Configuration key')
    
    config_set = config_subparsers.add_parser('set', help='Set configuration value')
    config_set.add_argument('key', help='Configuration key')
    config_set.add_argument('value', help='Configuration value')
    
    subparsers.add_parser('status', help='Show service status')
    subparsers.add_parser('test-print', help='Send a test print')
    
    queue_parser = subparsers.add_parser('queue', help='Manage print queue')
    queue_subparsers = queue_parser.add_subparsers(dest='queue_command')
    queue_subparsers.add_parser('list', help='List queue jobs')
    queue_subparsers.add_parser('clear', help='Clear all queue jobs')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    cli = LabelberryCLI()
    
    if args.command == 'config':
        if args.config_command == 'get':
            cli.config_get(getattr(args, 'key', None))
        elif args.config_command == 'set':
            cli.config_set(args.key, args.value)
        else:
            config_parser.print_help()
    
    elif args.command == 'status':
        cli.status()
    
    elif args.command == 'test-print':
        cli.test_print()
    
    elif args.command == 'queue':
        if args.queue_command == 'list':
            cli.queue_list()
        elif args.queue_command == 'clear':
            cli.queue_clear()
        else:
            queue_parser.print_help()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()