import base64
import os
import tempfile
from serpapi import GoogleSearch


def search_face(image_base64: str) -> dict:
    """
    Perform a reverse image search using SerpAPI's Google Lens endpoint.

    Takes a base64-encoded face image, uploads it to Google Lens via SerpAPI,
    and returns matching results prioritized by social media domains.

    Returns a dict with:
      - results: list of matched posts
      - total_results: number of results found
    
    Raises RuntimeError on API failures.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY environment variable is not set.")

    # Strip the data URI prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    image_bytes = base64.b64decode(image_base64)

    # Save to a temp file for SerpAPI upload
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        params = {
            "engine": "google_lens",
            "url": tmp_path,
            "api_key": api_key,
        }

        # SerpAPI Google Lens requires a URL, so we use the upload approach
        # For local files, we pass the file path and let SerpAPI handle it
        search = GoogleSearch(params)
        raw_results = search.get_dict()

        # Parse visual matches
        visual_matches = raw_results.get("visual_matches", [])

        # Social media domains to prioritize
        social_domains = [
            "instagram.com", "twitter.com", "x.com", "linkedin.com",
            "facebook.com", "tiktok.com", "youtube.com", "reddit.com",
            "pinterest.com", "tumblr.com",
        ]

        results = []
        for match in visual_matches[:20]:  # Check top 20
            link = match.get("link", "")
            source_domain = match.get("source", "")
            title = match.get("title", "")
            thumbnail = match.get("thumbnail", "")
            snippet = match.get("snippet", "")

            results.append({
                "title": title,
                "url": link,
                "thumbnail": thumbnail,
                "source": source_domain,
                "snippet": snippet,
                "is_social": any(d in link.lower() for d in social_domains),
            })

        # Sort: social media results first, then by order
        results.sort(key=lambda r: (not r["is_social"],))

        # Return top 5
        final_results = results[:5]

        # Remove the is_social flag from output
        for r in final_results:
            r.pop("is_social", None)

        return {
            "results": final_results,
            "total_results": len(final_results),
        }

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
