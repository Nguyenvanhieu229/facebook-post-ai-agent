import requests
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

FACEBOOK_API_VERSION = "v20.0"


@tool()
def post_to_facebook_page(post_text: str, image_path: Optional[str] = None) -> str:
    """
    Publishes a post to a Facebook Page with optional image.

    Args:
        post_text (str): The text content for the post
        image_path (Optional[str]): Local file path to image. If None or empty, posts text only.

    Returns:
        str: Success message with post link or error message
    """
    page_id = os.getenv("PAGE_ID")
    access_token = os.getenv("PAGE_ACCESS_TOKEN")

    if not all([page_id, access_token]):
        return "❌ Error: Please set PAGE_ID and PAGE_ACCESS_TOKEN in your .env file."

    base_url = f"https://graph.facebook.com/{FACEBOOK_API_VERSION}"

    # Check if we have an image to upload
    photo_id = None
    if image_path and image_path.strip() and os.path.exists(image_path):
        print("🖼️ Image provided, uploading to Facebook...")
        photo_id = _upload_image_to_facebook(base_url, page_id, access_token, image_path)
        if photo_id is None:
            return "❌ Failed to upload image. Aborting post creation."
    else:
        if image_path:
            print(f"⚠️ Image path provided but file not found: {image_path}")
        print("📝 No image provided, creating text-only post...")

    # Create the post
    return _create_facebook_post(base_url, page_id, access_token, post_text, photo_id)


def _upload_image_to_facebook(base_url: str, page_id: str, access_token: str, image_path: str) -> Optional[str]:
    """
    Upload image to Facebook and return photo ID

    Returns:
        Optional[str]: Photo ID if successful, None if failed
    """
    upload_url = f"{base_url}/{page_id}/photos"
    photo_params = {
        'access_token': access_token,
        'published': 'false'  # Upload but don't publish yet
    }

    try:
        with open(image_path, 'rb') as image_file:
            files = {'source': image_file}
            response = requests.post(upload_url, files=files, params=photo_params)
            response.raise_for_status()

        photo_data = response.json()
        photo_id = photo_data.get('id')

        if photo_id:
            print(f"✅ Image uploaded successfully with ID: {photo_id}")
            return photo_id
        else:
            print(f"❌ Failed to get photo ID from Facebook response: {photo_data}")
            return None

    except FileNotFoundError:
        print(f"❌ Error: The image file was not found at {image_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error during image upload: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Facebook error details: {e.response.text}")
        return None


def _create_facebook_post(base_url: str, page_id: str, access_token: str, post_text: str,
                          photo_id: Optional[str] = None) -> str:
    """
    Create Facebook post with or without image

    Returns:
        str: Success or error message
    """
    post_url = f"{base_url}/{page_id}/feed"
    post_params = {
        'access_token': access_token,
        'message': post_text
    }

    # Add image attachment if photo_id is provided
    if photo_id:
        post_params['attached_media[0]'] = f"{{'media_fbid': '{photo_id}'}}"
        print("🚀 Publishing post with image to Facebook Page...")
    else:
        print("🚀 Publishing text-only post to Facebook Page...")

    try:
        response = requests.post(post_url, params=post_params)
        response.raise_for_status()

        post_data = response.json()
        post_id = post_data.get('id')

        if post_id:
            post_type = "with image" if photo_id else "text-only"
            return f"🎉 POST PUBLISHED SUCCESSFULLY! ({post_type}) Post link: https://www.facebook.com/{post_id}"
        else:
            return f"❌ Error publishing post. Response: {post_data}"

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error during post creation: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Facebook error details: {e.response.text}")
        return f"❌ Connection error during post creation: {e}"


# Alternative tool for text-only posts (for backwards compatibility)
@tool()
def post_text_to_facebook_page(post_text: str) -> str:
    """
    Publishes a text-only post to a Facebook Page.

    Args:
        post_text (str): The text content for the post

    Returns:
        str: Success message with post link or error message
    """
    return post_to_facebook_page(post_text, None)