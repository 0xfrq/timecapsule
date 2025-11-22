import sys
from pillow_heif import register_heif_opener
register_heif_opener()
from PIL import Image
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata



def extract_image_metadata(file_path):
    try:
        img = Image.open(file_path)

        print("\n=== IMAGE METADATA ===")

        if "exif" in img.info:
            from PIL import ExifTags
            exif = img.getexif()
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                print(f"{tag}: {value}")
            return

        if hasattr(img, "_getexif") and img._getexif():
            exif_data = img._getexif()
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                print(f"{tag}: {value}")
            return

        print("No EXIF metadata found.")
        
    except Exception as e:
        print(f"Error reading image metadata: {e}")


def extract_video_metadata(file_path):
    print("\n=== VIDEO METADATA ===")
    parser = createParser(file_path)
    if not parser:
        print("Unable to parser file.")
        return
    
    with parser:
        metadata = extractMetadata(parser)
        if not metadata:
            print("No metadata found.")
            return


    for item in metadata.exportPlaintext():
        print(item)

def main():
    if len(sys.argv) < 2:
        print("Usage : python3 extract_metadata <file>")
        return
    file_path = sys.argv[1]
    print(f"Reading metadata from: {file_path}")

    try:
        extract_image_metadata(file_path)
    except:
        pass

    try:
        extract_video_metadata(file_path)
    except:
        pass


if __name__ == "__main__":
    main()
