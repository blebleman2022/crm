#!/usr/bin/env python3
import subprocess
import sys

def run_git_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd='/Users/blebleman/sync/SynologyDrive/CRM1'
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

print("=== Current Branch ===")
print(run_git_command("git branch --show-current"))

print("\n=== Last 5 Commits on Current Branch ===")
print(run_git_command("git log --oneline -5"))

print("\n=== Remote Branches ===")
print(run_git_command("git branch -r"))

print("\n=== Remote URL ===")
print(run_git_command("git remote -v"))

print("\n=== Status ===")
print(run_git_command("git status -sb"))

print("\n=== Last Commit Hash ===")
print(run_git_command("git rev-parse HEAD"))

print("\n=== Remote main Branch Hash ===")
print(run_git_command("git rev-parse origin/main"))

