import subprocess
import sys

def install_spacy_model():
    """Install the spaCy English language model."""
    print("Installing spaCy English language model...")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    print("Installation complete!")

if __name__ == "__main__":
    install_spacy_model() 