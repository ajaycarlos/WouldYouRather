import main
import youtube_upload
import history
import question_tracker

# Mock the upload and tracking functions so nothing goes to YouTube or pollutes your history
def mock_upload(*args, **kwargs):
    print("\n[TEST MODE] Mock upload triggered - video was NOT sent to YouTube.")
    return "TEST_VIDEO_ID"

youtube_upload.upload_video = mock_upload
history.save_entry = lambda *args, **kwargs: print("[TEST MODE] Skipped history save.")
question_tracker.save_used_question = lambda *args, **kwargs: print("[TEST MODE] Skipped question tracker save.")

if __name__ == "__main__":
    print("Running generation pipeline in TEST MODE...")
    main.main()
