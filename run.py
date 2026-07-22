"""
Script testare pentru demonstrație
Meniu interactiv cu toate comenzile
"""

import os
import sys
import subprocess


def run_cmd(cmd, desc):
    """Execută comandă și afișează rezultat"""
    print(f"\n{desc}...")
    print("-" * 50)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Eroare la {desc}")
    print()


def menu():
    """Meniu principal"""
    while True:
        print("\n" + "="*50)
        print("GESTIUNE DOWNLOAD-URI - MENIU TESTARE")
        print("="*50)
        print("\n1. Compilare (verifică sintaxă)")
        print("2. Teste unitare")
        print("3. Dry-run (simulare)")
        print("4. Rulare normală")
        print("5. Undo (anulare)")
        print("6. GUI (desktop)")
        print("7. Web app (localhost:5000)")
        print("8. Watcher (monitorizare)")
        print("9. Statistici")
        print("10. Log-uri")
        print("0. Ieșire")
        print("="*50)
        
        choice = input("\nAlege [0-10]: ").strip()
        
        if choice == "0":
            print("Gata!")
            sys.exit(0)
        
        elif choice == "1":
            run_cmd(
                "python3 -m py_compile proiect/*.py main.py gui.py web_app.py",
                "Compilare"
            )
        
        elif choice == "2":
            run_cmd(
                "python3 -m pytest tests/ -v",
                "Teste"
            )
        
        elif choice == "3":
            run_cmd(
                "python3 main.py --config config/config.yaml --dry-run",
                "Dry-run"
            )
        
        elif choice == "4":
            run_cmd(
                "python3 main.py --config config/config.yaml",
                "Rulare"
            )
        
        elif choice == "5":
            run_cmd(
                "python3 main.py --config config/config.yaml --undo",
                "Undo"
            )
        
        elif choice == "6":
            print("\nPornire GUI...")
            os.system("python3 gui.py")
        
        elif choice == "7":
            print("\nPornire Web App (http://localhost:5000)...")
            os.system("python3 web_app.py")
        
        elif choice == "8":
            run_cmd(
                "python3 main.py --config config/config.yaml --watch",
                "Watcher"
            )
        
        elif choice == "9":
            run_cmd(
                "cat config/stats.json",
                "Statistici"
            )
        
        elif choice == "10":
            run_cmd(
                "tail -50 logs/organizer.log",
                "Log-uri"
            )
        
        else:
            print("Optiune invalida!")
        
        input("\nApasă Enter pentru meniu...")


if __name__ == "__main__":
    # Activează venv
    if os.name == "posix":
        os.system("source venv/bin/activate")
    
    menu()