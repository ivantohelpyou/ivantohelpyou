import os
import re
import requests
import xml.etree.ElementTree as ET

# Paths
input_dir = "./showcase_xml"  # Directory containing XML files
output_dir = "./showcase"  # Directory to save converted Markdown files
images_dir = "./assets/images"  # Directory to save downloaded images

# Ensure output and images directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(images_dir, exist_ok=True)

# Define namespaces for WordPress XML
namespaces = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[^\w\-\.]', '_', filename)

# Function to download images
def download_image(url, output_dir):
    try:
        filename = sanitize_filename(os.path.basename(url))
        filepath = os.path.join(output_dir, filename)

        # Skip downloading if the file already exists
        if os.path.exists(filepath):
            print(f"Image already exists, skipping download: {filepath}")
            return filepath

        # Download the image
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded image: {filepath}")
            return filepath
        else:
            print(f"Failed to download image: {url} (Status code: {response.status_code})")
            return None
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

# Process each XML file
for filename in os.listdir(input_dir):
    if filename.endswith(".xml"):
        filepath = os.path.join(input_dir, filename)
        print(f"Processing file: {filepath}")
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # Create subdirectories for this XML file
            site_name = sanitize_filename(os.path.splitext(filename)[0])  # Use sanitized XML filename as site name
            site_output_dir = os.path.join(output_dir, site_name)
            site_images_dir = os.path.join(images_dir, site_name)
            os.makedirs(site_output_dir, exist_ok=True)
            os.makedirs(site_images_dir, exist_ok=True)

            # Extract <item> elements
            items = root.findall(".//item")
            if not items:
                print(f"No <item> elements found in {filename}. Check the XML structure.")
                continue

            for item in items:
                # Extract metadata
                title = item.find("title").text if item.find("title") is not None else "Untitled"
                date = item.find("wp:post_date", namespaces).text if item.find("wp:post_date", namespaces) is not None else "1970-01-01"
                content = item.find("content:encoded", namespaces).text if item.find("content:encoded", namespaces) is not None else "No content available."
                post_type = item.find("wp:post_type", namespaces).text if item.find("wp:post_type", namespaces) is not None else "post"

                # Skip non-post types (e.g., attachments)
                if post_type != "post":
                    print(f"Skipping non-post type: {post_type}")
                    continue

                # Sanitize title for slug
                slug = sanitize_filename(title.lower().replace(" ", "-"))

                # Process images in the content
                image_pattern = r'<img[^>]+src="([^"]+)"[^>]*>'
                caption_pattern = r'<figcaption[^>]*>(.*?)</figcaption>'
                images = re.findall(image_pattern, content)
                captions = re.findall(caption_pattern, content)

                # Download images and replace URLs in content
                for i, img_url in enumerate(images):
                    local_path = download_image(img_url, site_images_dir)
                    if local_path:
                        # Replace the image URL in the content with the local path
                        content = content.replace(img_url, f"/assets/images/{site_name}/{os.path.basename(local_path)}")
                        # Add caption if available
                        if i < len(captions):
                            content += f"\n\n*{captions[i]}*\n"

                # Ensure date is valid for Jekyll
                try:
                    date_prefix = date[:10]  # Extract YYYY-MM-DD
                except Exception:
                    date_prefix = "1970-01-01"

                # Create a Markdown file for each post
                output_file = os.path.join(site_output_dir, f"{date_prefix}-{slug}.md")
                print(f"Writing to file: {output_file}")
                with open(output_file, "w") as f:
                    f.write(f"---\n")
                    f.write(f"title: \"{title}\"\n")
                    f.write(f"date: {date}\n")
                    f.write(f"layout: post\n")
                    f.write(f"---\n\n")
                    f.write(content)
        except ET.ParseError as e:
            print(f"Error parsing XML file {filepath}: {e}")
        except Exception as e:
            print(f"Unexpected error processing file {filepath}: {e}")
    else:
        print(f"Skipping non-XML file: {filename}")