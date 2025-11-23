from datetime import datetime
import psycopg2
import requests
import random
import re

# ============== DATABASE CONFIG ==============
DB_HOST = "localhost"
DB_NAME = "timecapsule"
DB_USER = "postgres"
DB_PASS = "xxx"
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
def insta_detail_scraper(target_url, api_type):
    print(f"[INFO] Scraping details for URL: {target_url}...")
    url = "https://instagram-scraper-stable-api.p.rapidapi.com/get_media_data.php"
    
    querystring = {
        "reel_post_code_or_url": target_url,
        "type": api_type
    }
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if not data.get('id') and not data.get('pk'):
            print("[ERROR] Data not found or API Error (ID/PK missing).")
            return None
        
        # Scrape Media Type
        # 1=Photo, 2=Video, 8=Carousel
        ig_type = data.get('media_type')
        if ig_type == 2:
            media_type = 'video'
        else:
            media_type = 'photo'

        # Scrape URL
        code = data.get('code')
        clean_url = f"https://www.instagram.com/p/{code}"

        # Scrape Description
        description = ""
        if data.get('caption'):
            description = data['caption'].get('text', '')
        
        # Scrape Thumbnail
        try:
            thumb_url = data['image_versions2']['candidates'][0]['url']
        except (KeyError, IndexError, TypeError):
            thumb_url = ""

        # Scrape Year
        raw_time = int(data.get('taken_at', 0))
        if raw_time > 0:
            year = datetime.fromtimestamp(raw_time).year
        else:
            year = datetime.now().year

        # Scrape Tags
        tags = re.findall(r"#(\w+)", description)

        # For Comments
        ig_id = data.get('id')

        print("[INFO] Successfully retrieved post details.")
        return {
            "url": clean_url,
            "description": description,
            "media_type": media_type,
            "thumbnail": thumb_url,
            "year": year,
            "tags": tags,
            "ig_id": ig_id
        }

    except Exception as e:
        print(f"[ERROR] Exception in Detail Scraper: {e}")
        return None

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
        detail_data = insta_detail_scraper(input_url, api_type)
        
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