"""
Fetches free stock photos from Pexels (free API, no commercial-use restriction,
explicit license to use, modify, and even use commercially without attribution
required - though crediting is appreciated). Search term comes from Gemini's
image_query field per option.
"""
import io
import requests
from PIL import Image
import config
from retry_utils import retry

SEARCH_URL = "https://api.pexels.com/v1/search"


@retry(times=3, delay=5, backoff=3)
def fetch_image(query: str, out_path: str) -> str:
    headers = {"Authorization": config.PEXELS_API_KEY}
    resp = requests.get(SEARCH_URL, headers=headers, params={"query": query, "per_page": 5, "orientation": "portrait"}, timeout=20)
    resp.raise_for_status()
    results = resp.json().get("photos", [])

    if not results:
        # Fall back to a broader/simpler query if the specific one has no matches
        resp = requests.get(SEARCH_URL, headers=headers, params={"query": query.split()[0], "per_page": 5}, timeout=20)
        resp.raise_for_status()
        results = resp.json().get("photos", [])

    if not results:
        raise ValueError(f"No Pexels image found for query: '{query}'")

    image_url = results[0]["src"]["large"]
    img_resp = requests.get(image_url, timeout=20)
    img_resp.raise_for_status()
    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    fetch_image("einstein portrait", "output/test_image.jpg")
    print("Saved output/test_image.jpg")
