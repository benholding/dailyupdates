from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import datetime
import logging
import time
from kaggle.api.kaggle_api_extended import KaggleApi
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SENT_ARTICLES_FILE = 'sent_articles.txt'

def fetch_google_scholar_updates(queries, days_ago=7):
    updates = {query: [] for query in queries}
    today = datetime.datetime.now().date()
    start_date = today - datetime.timedelta(days=days_ago)

    sent_articles = load_sent_articles()

    for query in queries:
        url = f"https://scholar.google.com/scholar?hl=en&as_sdt=0,5&q={query.replace(' ', '+')}&scisbd=1"
        logging.info(f"Fetching URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            logging.info(f"Response status: {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')
            logging.info(f"HTML content snippet: {soup.prettify()[:1000]}")

            if not soup:
                logging.error("Failed to parse HTML")
                continue

            entries = soup.find_all('div', class_='gs_r gs_or gs_scl')
            logging.info(f"Found {len(entries)} entries")

            for entry in entries:
                logging.info(f"Entry HTML: {entry.prettify()[:500]}")

                title_tag = entry.find('h3', class_='gs_rt')
                if title_tag and title_tag.a:
                    title = title_tag.text.strip()
                    link = title_tag.a['href']
                    pub_info = entry.find('div', class_='gs_a').text
                    pub_date = None
                    pub_date_str = None

                    date_tag = entry.find('span', class_='gs_age') or entry.find('div', class_='gs_rs')
                    if date_tag:
                        relative_date_str = date_tag.text.strip()
                        logging.info(f"Relative date string: {relative_date_str}")

                        if "days ago" in relative_date_str:
                            days_ago = int(relative_date_str.split(" ")[0])
                            pub_date = today - datetime.timedelta(days=days_ago)
                        elif "day ago" in relative_date_str:
                            pub_date = today - datetime.timedelta(days=1)
                        elif "hours ago" in relative_date_str or "hour ago" in relative_date_str:
                            pub_date = today

                        if pub_date and start_date <= pub_date <= today:
                            pub_date_str = pub_date.strftime('%Y-%m-%d')
                            if link not in sent_articles:
                                updates[query].append({'title': title, 'link': link, 'date': pub_date_str})
                                logging.info(f"Added update: {title} ({pub_date_str}): {link}")

            logging.info(f'Fetched {len(updates[query])} updates from Google Scholar for query: {query}')
            time.sleep(10)  # Sleep for 10 seconds to avoid getting blocked
        except requests.RequestException as e:
            logging.error(f'Error fetching Google Scholar updates for query: {query}, error: {e}')

    return updates

def load_sent_articles():
    if not os.path.exists(SENT_ARTICLES_FILE):
        return set()

    with open(SENT_ARTICLES_FILE, 'r') as file:
        return set(file.read().splitlines())

def save_sent_articles(articles):
    with open(SENT_ARTICLES_FILE, 'a') as file:
        for article in articles:
            file.write(article['link'] + '\n')

def fetch_kaggle_updates(queries):
    updates = []
    api = KaggleApi()
    api.authenticate()

    for query in queries:
        try:
            competitions = api.competitions_list(search=query)
            for comp in competitions:
                updates.append({'title': comp.title, 'link': comp.ref, 'date': comp.deadline.strftime('%Y-%m-%d')})
            logging.info(f'Fetched {len(competitions)} updates from Kaggle for query: {query}')
        except Exception as e:
            logging.error(f'Error fetching Kaggle updates for query: {query}, error: {e}')

    return updates

def compose_email_body(google_updates, kaggle_updates):
    body = "<html><body>"
    for query, articles in google_updates.items():
        if articles:
            body += f"<b>Google Scholar Updates for '{query}':</b><br>" + "<br>".join([f"{u['title']} ({u['date']}): <a href='{u['link']}'>{u['link']}</a>" for u in articles]) + "<br><br>"

    body += "<b>Kaggle Updates:</b><br>" + "<br>".join([f"{u['title']} ({u['date']}): <a href='{u['link']}'>{u['link']}</a>" for u in kaggle_updates]) + "<br><br>"
    body += "</body></html>"
    return body

def send_email(subject, body, to_email):
    from_email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))  # Change here to send HTML email

    try:
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        logging.info('Email sent successfully.')
    except Exception as e:
        logging.error(f'Failed to send email: {e}')


# Main function
def lambda_handler(event, context):
    google_queries = [
        '"Data Science" AND "Video Games" AND (analytics OR "game design" OR "player behavior" OR "user data")',
        '"Game Analytics" AND (insights OR "player data" OR metrics OR reporting OR "real-time analytics")',
        '"Machine Learning" AND "Video Games" AND (applications OR techniques OR outcomes OR implementation OR "case studies")',
        '"Predictive Modeling" AND "Video Games" AND (player behavior OR engagement OR retention OR churn OR "user segmentation")',
        '"User Experience" AND "Video Games" AND (design OR feedback OR usability OR interface OR UX OR "player satisfaction")',
        '"Ubisoft" AND "machine learning" AND (games OR AI applications OR analytics OR "data science" OR "player insights")',
        '"Nintendo" AND "machine learning" AND (game development OR AI OR innovation OR "data analytics" OR "game design")',
        '"AI" AND "Video Games" AND (development OR gameplay OR "game AI" OR NPCs OR "procedural generation" OR "adaptive AI")',
        '"esport" AND "machine learning" AND (analytics OR predictions OR strategies OR performance OR "player performance" OR moderation)',
        '"video game" AND "recommendation system" AND (algorithm OR user preferences OR machine learning OR personalization OR "content recommendation")',
        '"player engagement" AND "video games" AND (retention OR behavior OR metrics OR gamification OR "engagement strategies")',
        '"IEEE conference on games" AND (papers OR proceedings OR research OR publications OR "conference papers")',
        '"gameplay" AND (analysis OR patterns OR user experience OR feedback OR usability OR "game mechanics")',
        '"telemetry" AND game AND (analysis OR metrics OR insights OR "performance tracking" OR "real-time data")',
        '"player behavior" AND "video games" AND (analysis OR modeling OR prediction OR metrics OR "behavioral patterns")',
        '"Activision Blizzard" AND ("machine learning" OR AI OR analytics OR "data science" OR "player data")',
        '"Electronic Arts" AND ("machine learning" OR AI OR analytics OR "data science" OR "game insights")',
        '"Sony Interactive Entertainment" AND ("machine learning" OR AI OR analytics OR "data science" OR "user data")',
        '"Microsoft Studios" AND ("machine learning" OR AI OR analytics OR "data science" OR "game analytics")',
        '"game development" AND ("data science" OR "machine learning" OR AI OR analytics OR "game design")',
        '"video game AI" AND (development OR algorithms OR procedural generation OR NPC behavior OR "adaptive AI")',
        '"video game data" AND ("data science" OR analytics OR metrics OR analysis OR "user data")',
        '"game user research" AND ("video games" OR "game development" OR "player experience" OR "user testing")',
        '"game AI" AND ("machine learning" OR neural networks OR deep learning OR reinforcement learning OR "game algorithms")',
        '"procedural content generation" AND ("video games" OR "game design" OR AI OR "game development")',
        '"neural networks" AND ("video games" OR "game development" OR "game design")',
        '"deep learning" AND ("video games" OR "game development" OR "game analytics")',
        '"reinforcement learning" AND ("video games" OR "game development" OR "game design")',
        '"game data mining" AND ("video games" OR "player behavior" OR "data analysis" OR "user insights")',
        '"player retention" AND ("video games" OR "game analytics" OR "predictive modeling" OR "engagement strategies")',
        '"player churn" AND ("video games" OR "game analytics" OR "predictive modeling" OR "user behavior")',
        '"game recommendation algorithms" AND ("video games" OR "machine learning" OR AI OR "user preferences")',
        '"AI in game design" AND ("video games" OR "game development" OR "game design" OR "adaptive AI")',
        '"game performance metrics" AND ("video games" OR "player behavior" OR "data analytics" OR "performance analysis")',
        '"data-driven game design" AND ("video games" OR "game development" OR "analytics" OR "player insights")',
        '"game AI research" AND ("video games" OR "machine learning" OR AI OR "game development")',
        '"game testing" AND ("video games" OR "user experience" OR "QA" OR "game development")',
        '"game user feedback" AND ("video games" OR "user experience" OR "game development")',
        '"video game success" AND ("analytics" OR "metrics" OR "data analysis")',
        '"video game monetization" AND ("data analytics" OR "player behavior")',
        '"biometrics" AND "video game"'
    ]


    kaggle_queries = [
        'Video Game',
        'player',
        'gameplay',
        'Game Analytics',
        'Player Behavior',
        'Gaming AI',
        'Game Development',
        'Esports',
        'Gaming Recommendations',
        'Virtual Reality',
        'Augmented Reality'
    ]

    google_updates = fetch_google_scholar_updates(google_queries)
    kaggle_updates = fetch_kaggle_updates(kaggle_queries)

    if any(google_updates.values()) or kaggle_updates:
        body = compose_email_body(google_updates, kaggle_updates)
        send_email("Daily Data Science Updates", body, os.getenv('EMAIL_ADDRESS'))
        all_google_updates = [article for articles in google_updates.values() for article in articles]
        save_sent_articles(all_google_updates)
    else:
        logging.info('No updates to send today.')

if __name__ == "__main__":
    lambda_handler(None, None)
