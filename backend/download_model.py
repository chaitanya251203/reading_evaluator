from faster_whisper import download_model

def main():
    print("Downloading Whisper 'medium' model (~1.5GB)...")
    print("This will show a progress bar. Please wait.")
    
    # download_model automatically uses tqdm to show a progress bar
    model_path = download_model("medium")
    
    print(f"\nModel successfully downloaded to: {model_path}")
    print("You can now start the backend with: uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()
