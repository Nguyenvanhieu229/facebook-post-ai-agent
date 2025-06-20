import time
import requests
from typing import List, Dict, Any, Set

from langchain_community.document_loaders import WebBaseLoader
from main import run_agent_pipeline

# --- CONSTANTS ---
SUBREDDIT_TO_SCRAPE = "learnprogramming"
POST_FETCH_LIMIT = 1
MIN_SCORE_THRESHOLD = 100
REDDIT_API_USER_AGENT = 'MyCoolBot/1.0'
RUN_INTERVAL_SECONDS = 30000


# --- UTILITY FUNCTIONS ---
def get_reddit_posts(subreddit: str, limit: int) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {'User-Agent': REDDIT_API_USER_AGENT}
    print(f"Fetching data from r/{subreddit}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('data', {}).get('children', [])
    except requests.exceptions.RequestException as e:
        print(f"Error calling Reddit API: {e}")
        return []


def get_full_content(post_data: Dict[str, Any]) -> str:
    post_title = post_data.get('title', '')
    if post_data.get('is_self', False):
        return post_data.get('selftext', '')

    url = post_data.get('url', '')
    is_external_article = any(
        ext in url for ext in ['.html', '.com', '.net', '.org', '.vn']) and 'reddit.com' not in url

    if is_external_article:
        print(f"-> Scraping external link: {url}")
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()
            return docs[0].page_content
        except Exception as e:
            print(f"-> Could not fetch content from link: {e}")
            return f"Could not fetch content from the link. The title is: {post_title}"

    return f"The post content is media (image/video). Write an article based on the following title: \"{post_title}\""


# --- CORE BOT LOGIC ---
def run_bot_cycle(processed_ids: Set[str]) -> Set[str]:
    print("\n--- Starting new scan cycle ---")
    raw_posts = get_reddit_posts(SUBREDDIT_TO_SCRAPE, POST_FETCH_LIMIT)

    if not raw_posts:
        print("No posts were fetched in this cycle.")
        return processed_ids

    new_posts_found = 0
    for raw_post in raw_posts:
        post_data = raw_post['data']
        post_id = post_data.get('id')
        score = post_data.get('score', 0)

        if post_id and post_id not in processed_ids and score >= MIN_SCORE_THRESHOLD:
            new_posts_found += 1
            print(f"\n✅ Found a new suitable post: \"{post_data['title']}\" (Score: {score})")

            processed_ids.add(post_id)

            full_content = get_full_content(post_data)
            if full_content:
                run_agent_pipeline(full_content)

    if new_posts_found == 0:
        print("No new suitable posts found in this scan.")

    return processed_ids


# --- MAIN EXECUTION LOOP ---
def main():
    processed_post_ids: Set[str] = set()
    try:
        while True:
            processed_post_ids = run_bot_cycle(processed_post_ids)
            print(f"\n--- Cycle finished. Waiting for {RUN_INTERVAL_SECONDS} seconds... ---")
            time.sleep(RUN_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nReceived stop command. Exiting gracefully!")


if __name__ == "__main__":
    main()
