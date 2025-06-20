import base64
import os
import time
import binascii
from typing import Optional
from langchain_core.tools import tool


@tool()
def save_base64_as_image(base64_string: str, output_folder: str = "generated_images") -> Optional[str]:
    """
        Saves a base64 encoded image string to a local file.
        Returns the absolute path to the saved image file upon success.
        """

    try:
        os.makedirs(output_folder, exist_ok=True)

        image_data = base64.b64decode(base64_string)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"image_{timestamp}.png"
        output_filepath = os.path.join(output_folder, filename)

        with open(output_filepath, "wb") as f:
            f.write(image_data)

        absolute_path = os.path.abspath(output_filepath)
        print(f"✅ Image saved successfully at: {absolute_path}")
        return absolute_path

    except (binascii.Error, TypeError) as e:
        return f"❌ Error decoding base64 string: {e}"
    except IOError as e:
        return f"❌ Error saving the image file: {e}"
    except Exception as e:
        return f"❌ An unexpected error occurred: {e}"


if __name__ == '__main__':
    sample_base64_string = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB" \
                           "/epv2AAAAABJRU5ErkJggg=="

    print("Attempting to save image from sample base64 string...")

    saved_path = save_base64_as_image(sample_base64_string)

    if saved_path:
        print(f"\nProcess completed. Check the file at the path printed above.")
    else:
        print("\nThe process failed.")
