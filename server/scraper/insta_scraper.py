from datetime import datetime
import psycopg2
import requests
import random
import re

# ============== DATABASE CONFIG ==============
DB_HOST = "localhost"
DB_NAME = "timecapsule"
DB_USER = "postgres"
DB_PASS = "123"
# =============================================

# --- URL PROCESSING ---
def parse_insta_url(url):
    # Regex to find code after /p/ or /reel/
    pattern = r"(?:p|reel|tv)/([A-Za-z0-9_-]+)"
    match = re.search(pattern, url)
    
    if match:
        shortcode = match.group(1)
        if "/reel/" in url:
            api_type = "reel"
        else:
            api_type = "post"

        print(f"[INFO] Shortcode found: {shortcode} (Type: {api_type})")
        return shortcode, api_type
    
    print("[ERROR] Invalid URL or Shortcode not found.")
    return None, None

# --- DETAILS SCRAPER ---
def insta_detail_scraper(target_url, shortcode_input, api_type):
    print(f"[INFO] Scraping details for URL: {target_url}...")
    URL_API_VISUAL = "https://instagram-scraper-stable-api.p.rapidapi.com/get_media_data_v2.php"
    URL_API_TEXT   = "https://instagram-scraper-stable-api.p.rapidapi.com/get_reel_title.php"
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
    }

    # Variabel
    clean_url = f"https://www.instagram.com/p/{shortcode_input}"
    thumbnail_url = ""
    media_type_db = "photo"
    description = ""
    year = datetime.now().year
    ig_id = None
    tags = []

    # Visual & Metadata
    try:
        qs_visual = {"media_code": shortcode_input}
        
        print("   -> Requesting Visual Data...")
        res_vis = requests.get(URL_API_VISUAL, headers=headers, params=qs_visual)
        data_vis = res_vis.json()

        # For Comments
        ig_id = data_vis.get('id')
        if not ig_id:
            print("[ERROR] ID tidak ditemukan di API Visual.")
            return None

        # Scrape Thumbnail
        thumbnail_url = data_vis.get('thumbnail_src', '')

        # Scrape Media Type
        if data_vis.get('is_video'):
            media_type_db = 'video'
        else:
            media_type_db = 'photo'

        # Scrape Year
        raw_time = data_vis.get('taken_at_timestamp') or data_vis.get('taken_at')
        if raw_time > 0:
            year = datetime.fromtimestamp(raw_time).year
        else:
            year = datetime.now().year

    except Exception as e:
        print(f"[ERROR] Failed to scrape visual data: {e}")
        return None

    # Text & Description
    try:
        qs_text = {
            "reel_post_code_or_url": target_url,
            "type": api_type
        }
        
        print("   -> Requesting Text Data...")
        res_text = requests.get(URL_API_TEXT, headers=headers, params=qs_text)
        data_text = res_text.json()

        # Scrape Description
        description = data_text.get('post_caption', '')
        
        # If post_caption empty, try title
        if not description:
            description = data_text.get('title', '')

        # Scrape Tags
        tags = re.findall(r"#(\w+)", description)

    except Exception as e:
        print(f"[WARNING] Failed to scrape text data: {e}")
        # Tidak return None, karena kita masih punya data visual yang valid

    print("[INFO] Successfully retrieved post details.")
    return {
        "url": clean_url,
        "description": description,
        "media_type": media_type_db,
        "thumbnail": thumbnail_url,
        "year": year,
        "tags": tags,
        "ig_id": ig_id
    }

# --- SAVE DETAILS TO DB ---
def insta_detail_db(data):
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()
        
        # Insert into post
        query_post = """
            INSERT INTO post (url, media_type, description, thumb_url)
            VALUES (%s, %s, %s, %s)
            RETURNING post_id;
        """
        cur.execute(query_post, (
            data['url'], 
            data['media_type'], 
            data['description'],
            data['thumbnail']
        ))
        post_id = cur.fetchone()[0]

        # Insert into time
        cur.execute("INSERT INTO time (post_id, year) VALUES (%s, %s);", (post_id, data['year']))

        # Insert into tag & post_tag
        for tag_name in data['tags']:
            cur.execute("INSERT INTO tag (tag_name) VALUES (%s) ON CONFLICT (tag_name) DO NOTHING;", (tag_name,))
            cur.execute("SELECT tag_id FROM tag WHERE tag_name = %s;", (tag_name,))
            tag_id = cur.fetchone()[0]
            
            cur.execute("INSERT INTO post_tag (post_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (post_id, tag_id))
            
        conn.commit()
        cur.close()
        print(f"[SUCCESS] Post IG saved to Database (ID: {post_id})")
        return post_id

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"[ERROR] Database Error: {error}")
    finally:
        if conn is not None:
            conn.close()

# --- REPLIES SCRAPER ---
def insta_reply_scraper(post_id_ig, comment_id):
    url = "https://instagram-scraper-stable-api.p.rapidapi.com/get_post_child_comments.php"
    
    querystring = {
        "post_id": post_id_ig, 
        "comment_id": comment_id
    }
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        replies_list = []
        if data.get('child_comments'):
            # MAX 5 Replies
            for rep in data['child_comments'][:5]:
                replies_list.append({
                    "text": rep.get('text', '')
                })
        return replies_list
    except Exception:
        # Silent error handling
        return []

# --- COMMENTS SCRAPER ---
def insta_comment_scraper(shortcode, post_id_ig):
    print("[INFO] Scraping comments...")
    url = "https://instagram-scraper-stable-api.p.rapidapi.com/get_post_comments.php"
    
    querystring = {
        "media_code": shortcode,
        "sort_order": "popular"
    }
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        final_comments = []

        if data.get('comments'):
            # MAX 20 Comments
            for com in data['comments'][:20]:
                comment_id = com.get('pk') # IG Comments ID (for replies)
                
                comment_obj = {
                    "text": com.get('text', ''),
                    "replies": []
                }
                
                # Check if replies > 0
                child_count = com.get('child_comment_count', 0)
                if child_count > 0:
                    comment_obj['replies'] = insta_reply_scraper(post_id_ig, comment_id)
                
                final_comments.append(comment_obj)
        
        print(f"[INFO] Successfully retrieved {len(final_comments)} main comments.")
        return final_comments

    except Exception as e:
        print(f"[ERROR] Failed to scrape comments: {e}")
        return []

# --- SAVE COMMENTS TO DB ---
def insta_comment_db(post_id_db, comments_data):
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()
        
        # Insert into comments query
        query_insert = """
            INSERT INTO comments (post_id, user_id, text, parent_comment_id)
            VALUES (%s, %s, %s, %s)
            RETURNING comment_id;
        """
        
        for parent in comments_data:
            random_user = random.randint(1, 20)
            
            # Insert into comments
            cur.execute(query_insert, (
                post_id_db, 
                random_user, 
                parent['text'], 
                None
            ))
            parent_db_id = cur.fetchone()[0]
            
            # Insert replies into comments
            for reply in parent['replies']:
                random_user_reply = random.randint(1, 20)
                
                cur.execute(query_insert, (
                    post_id_db, 
                    random_user_reply, 
                    reply['text'], 
                    parent_db_id
                ))
            
        conn.commit()
        cur.close()
        print("[SUCCESS] All comments and replies successfully saved.")
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"[ERROR] Database Error (Comment): {error}")
    finally:
        if conn is not None:
            conn.close()


# ================= MAIN PROGRAM =================
if __name__ == "__main__":
    input_url = "https://www.instagram.com/p/DRKUtIAjHdt/" 
    
    # 1. Parse URL
    shortcode, api_type = parse_insta_url(input_url)
    
    if shortcode:
        # 2. Scrape Details
        detail_data = insta_detail_scraper(input_url, shortcode, api_type)
        
        if detail_data:
            post_id_ig = detail_data.get('ig_id') 
            
            # 3. Save Details Into DB
            post_id_db = insta_detail_db(detail_data)
            
            if post_id_db and post_id_ig:
                # 4. Scrape Comments
                comments_data = insta_comment_scraper(shortcode, post_id_ig)
                
                if comments_data:
                    # 5. Save Comments Into DB
                    insta_comment_db(post_id_db, comments_data)