import functions_framework
from google import genai
from google.genai import types
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
import logging
import google.cloud.logging
from google.cloud import secretmanager

# 1. Initialize Structured Logging
log_client = google.cloud.logging.Client()
log_client.setup_logging()

# 1. Define the AI Agent with Search capabilities
logging.info("Step 1: Agent Started.")

# Initialize Vertex AI
PROJECT_ID = os.environ.get("GCP_PROJECT")
client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")


def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

@functions_framework.http
def run_news_agent(request):

    try:
        logging.info("Step 2: Configuring Search Tool.")
        search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        logging.info("Step 3: Calling Gemini 2.5 (This can take 60+ seconds).")
        
        #model = GenerativeModel("gemini-3-pro-preview")

        prompt = """
            Role: Senior Strategic Intelligence Analyst for Google Cloud.

            Task: Perform a comprehensive scan of the internet to identify major industry announcements, product launches, and strategic shifts made in the last 7 days

            Scope of Research:
                1 - Cloud Computing: Updates from hyperscalers (AWS, Azure, GCP), innovations in serverless/containers, sovereign cloud developments, and major enterprise migrations.
                2 - Artificial Intelligence: New LLM releases, breakthroughs in agentic AI, significant AI hardware/TPU/NPU news, and major regulatory or AI safety shifts.
                3 - Cybersecurity: Critical zero-day vulnerabilities, major corporate breach post-mortems, new AI-driven security tools, and federal/global security directives (e.g., CISA updates).

            Audience: Google Cloud Executives (C-Suite and VP level).

            Output Format: "The Cloud & AI Executive Briefing" (Newsletter Style)
            1 - Structure: Use a clean, bulleted list categorized by the three pillars above.
                1a - Use <h3> for titles.
                2a - Use <ul> and <li> for bullet points.
                3a - Use <p> for paragraphs.
                4a - Use <a href="..."> links for sources.
                5a - DO NOT use Markdown (like ** or *). Use only HTML tags.
            2 - Content per Item: * Headline: Bold and descriptive.
                2a - Executive Summary: 2 sentences focusing on why it matters (competitive threat, market opportunity, or technical milestone).
                2b - Strategic Impact: A brief "Bottom Line" for Google Cloud.
                2c - Source: Direct link to the announcement or primary reporting.

            Strict Constraints:
                1 - Timeframe: Absolutely NO news older than 7 days.
                2 - Signal-to-Noise: Only include high-impact news. Ignore minor feature updates or routine blog posts.
                3 - Tone: Professional, objective, and high-density.
        """

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[search_tool]
            )
        )
        
        # Verify if the response contains text (Grounding can sometimes return empty 
        # if the search fails, so we handle that)
        if not response.text:
            news_summary = "No news found for the given criteria."
        else:
            news_summary = response.text

        logging.info("Step 4: AI summary generated successfully.")

        logging.info("Step 5: Retrieving SendGrid Key.")
        sg_key = get_secret("SENDGRID_API_KEY")
        
        # Define your list of recipients here
        recipient_list = [
            'your-email@gmail.com',
            'second-email@gmail.com'
        ]
        
        message = Mail(
            from_email='christopher.t.perry2@gmail.com',
            to_emails=recipient_list,
            subject='Weekly AI News Pulse (Gemini 3)',
            html_content=f"<h3>Weekly News Summary</h3>{news_summary}"
        )

        sg = SendGridAPIClient(sg_key)
        sg.send(message)
        logging.info("Step 6: Email Sent.")

        return "Report sent successfully", 200

    except Exception as e:
        # This will print the EXACT error to your Cloud Logs
        logging.error(f"CRASH in run_news_agent: {str(e)}", exc_info=True)
        return f"Error occurred: {str(e)}", 500
