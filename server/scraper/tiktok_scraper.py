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
def extract_id(url):
    # Regex to find numbers after 'video/' or 'photo/'
    pattern = r"(?:video|photo)/(\d+)"
    match = re.search(pattern, url)
    
    if match:
        print(f"[INFO] ID found: {match.group(1)}")
        return match.group(1)
    else:
        print("[ERROR] Invalid URL or ID not found.")
        return None

# --- DETAILS SCRAPER ---
def tiktok_detail_scraper(video_id):
    print(f"[INFO] Scraping details for ID: {video_id}...")
    url = "https://tiktok-api23.p.rapidapi.com/api/post/detail"
    querystring = {"videoId": video_id}
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if data.get('statusCode') == 0:
            post = data['itemInfo']['itemStruct']

            # Scrape URL, Thumbnail, and Media Type
            if post.get('imagePost'): # If true, it's a photo media type
                media_type = 'photo'
                url = f"https://www.tiktok.com/photo/{post['id']}"
                try:
                    thumbnail_url = post['imagePost']['images'][0]['imageURL']['urlList'][0]
                except (IndexError, KeyError):
                    thumbnail_url = ""
            else:
                media_type = 'video'
                url = f"https://www.tiktok.com/video/{post['id']}"
                video_info = post.get('video', {})
                thumbnail_url = video_info.get('cover', '')

            # Scrape Description
            description = post.get('desc', '')
            
            # Scrape Year
            raw_time = int(post.get('createTime', 0))
            if raw_time > 0:
                year = datetime.fromtimestamp(raw_time).year
            else:
                year = datetime.now().year

            # Scrape Tags
            tags = re.findall(r"#(\w+)", description)
            
            print("[INFO] Successfully retrieved post details.")
            return {
                "url": url,
                "description": description,
                "media_type": media_type,
                "thumbnail": thumbnail_url,
                "year": year,
                "tags": tags
            }
        else:
            print("[ERROR] Failed to retrieve details (API Status != 0).")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to scrape details: {e}")
        return None

# --- SAVE DETAILS TO DB ---
def tiktok_detail_db(data):
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
        query_time = "INSERT INTO time (post_id, year) VALUES (%s, %s);"
        cur.execute(query_time, (post_id, data['year']))

        # Insert into tag & post_tag
        for tag_name in data['tags']:
            cur.execute("INSERT INTO tag (tag_name) VALUES (%s) ON CONFLICT (tag_name) DO NOTHING;", (tag_name,))
            cur.execute("SELECT tag_id FROM tag WHERE tag_name = %s;", (tag_name,))
            tag_id = cur.fetchone()[0]
            
            cur.execute("INSERT INTO post_tag (post_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (post_id, tag_id))
            
        conn.commit()
        cur.close()
        
        print(f"[SUCCESS] Details saved to Database (Post ID: {post_id})")
        return post_id
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"[ERROR] Database Error (Detail): {error}")
    finally:
        if conn is not None:
            conn.close()

# --- REPLIES SCRAPER ---
def tiktok_reply_scraper(video_id, comment_id):
    url = "https://tiktok-api23.p.rapidapi.com/api/post/comment/replies"
    # MAX 5 Replies
    querystring = {"videoId": video_id, "commentId": comment_id, "count": "5", "cursor": "0"}
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        replies_list = []
        # Check if 'comments' is in response
        if data.get('comments'): 
            for rep in data['comments']:
                replies_list.append({
                    "text": rep.get('text', '')
                })
        return replies_list
    except Exception:
        # Silent error handling
        return []

# --- COMMENTS SCRAPER ---
def tiktok_comment_scraper(video_id):
    print("[INFO] Scraping comments...")
    url = "https://tiktok-api23.p.rapidapi.com/api/post/comments"
    # MAX 20 Comments
    querystring = {"videoId": video_id, "count": "20", "cursor": "0"}
    
    headers = {
        "x-rapidapi-key": "31b6bb776fmshf2f28b986086358p1bdcc1jsn15e4b0eb8f34",
        "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        final_comments = []

        if data.get('comments'):
            for com in data['comments']:
                cid = com.get('cid') # Tiktok Comments ID (for replies)
                
                comment_obj = {
                    "text": com.get('text', ''),
                    "replies": []
                }
                
                reply_count = com.get('reply_comment_total', 0)
                if reply_count > 0:
                    comment_obj['replies'] = tiktok_reply_scraper(video_id, cid)
                
                final_comments.append(comment_obj)

        print(f"[INFO] Successfully retrieved {len(final_comments)} main comments.")
        return final_comments
    
    except Exception as e:
        print(f"[ERROR] Failed to scrape comments: {e}")
        return []

# --- SAVE COMMENTS TO DB ---
def tiktok_comment_db(post_id, comments_data):
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
                post_id, 
                random_user, 
                parent['text'], 
                None
            ))
            parent_db_id = cur.fetchone()[0]
            
            # Insert replies into comments
            for reply in parent['replies']:
                random_user_reply = random.randint(1, 20)
                
                cur.execute(query_insert, (
                    post_id, 
                    random_user_reply, 
                    reply['text'], 
                    parent_db_id
                ))
            
        conn.commit()
        cur.close()
        print("[SUCCESS] All comments and replies successfully saved.")
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"[ERROR] Database Error (Detail): {error}")
    finally:
        if conn is not None:
            conn.close()


# ================= MAIN PROGRAM =================
if __name__ == "__main__":
    input_url = "https://www.tiktok.com/@_jokesmemes/video/7442071451814972694"
    
    # 1. Convert URL
    video_id = extract_id(input_url)
    
    if video_id:
        # 2. Scrape Detail
        hasil_detail = tiktok_detail_scraper(video_id)
        
        if hasil_detail:
            # 3. Save Details Into DB
            post_id_db = tiktok_detail_db(hasil_detail)
            
            # 4. Scrape Comments
            hasil_komentar = tiktok_comment_scraper(video_id)
            
            if hasil_komentar:
                # 5. Save Comments Into DB
                tiktok_comment_db(post_id_db, hasil_komentar)