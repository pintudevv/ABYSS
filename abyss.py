import sys
from backend.abyss_cli import run_cli_scanner, print_neutralized_status, scan_url_cli

def main():
    if "--url" in sys.argv:
        idx = sys.argv.index("--url")
        if idx + 1 < len(sys.argv):
            scan_url_cli(sys.argv[idx + 1])
        else:
            print("Usage: abyss --url <website_link>")
    elif "--status" in sys.argv:
        print_neutralized_status()
    elif "--boot-scan" in sys.argv:
        print("\n[!] ABYSS Boot Guard: Running Automated Windows Startup Scan...")
        run_cli_scanner()
    else:
        run_cli_scanner()

if __name__ == "__main__":
    main()
