import getpass
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from facebook_post import post_to_facebook_page
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.pydantic_v1 import BaseModel, Field

load_dotenv()

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google AI API key: ")

# LLM chính cho các tác vụ text
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

topic_parser = JsonOutputParser()


def create_topic_classifier_agent():
    prompt_template = ChatPromptTemplate.from_messages([
        ("system",
         "You are an expert content analyst. Classify the provided article into one of the following topics: "
         "'Web Development', 'Application Development', 'Artificial Intelligence (AI)', or 'Embedded & IoT "
         "Programming'. "
         "Return only a single JSON object with the key 'topic' and the chosen topic as the value."),
        ("human", "{article_text}\n\n{format_instructions}")
    ])
    return prompt_template | llm | topic_parser


def create_facebook_post_writer_agent():
    prompt_template = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professional Community Manager. Write an engaging Facebook post "
         "based on the provided content. Use friendly tone, add hashtags. "
         "NO MARKDOWN formatting. Plain text only. Maximum 200 words."),
        ("human",
         "Article: {article_text}\nTopic: {topic}")
    ])
    return prompt_template | llm | StrOutputParser()


class FacebookPostWriterInput(BaseModel):
    article_text: str = Field(description="The article text")
    topic: str = Field(description="The classified topic")


def get_tools() -> list:
    # Tạo chains
    topic_classifier_chain = create_topic_classifier_agent()
    facebook_post_writer_chain = create_facebook_post_writer_agent()

    # Tạo tools
    topic_classifier_tool = Tool(
        name="TopicClassifier",
        func=lambda text: topic_classifier_chain.invoke({
            "article_text": text[:2000],  # Truncate để tránh quá token
            "format_instructions": topic_parser.get_format_instructions()
        }),
        description="Classifies article topic. Input: article text (max 2000 chars)."
    )

    facebook_post_writer_tool = Tool(
        name="FacebookPostWriter",
        func=lambda article_and_topic: facebook_post_writer_chain.invoke({
            "article_text": article_and_topic.split("|||")[0][
                            :1500] if "|||" in article_and_topic else article_and_topic[:1500],
            "topic": article_and_topic.split("|||")[1] if "|||" in article_and_topic else "Unknown"
        }),
        description="Writes Facebook post. Input format: 'article_text|||topic' (separated by |||)."
    )

    return [
        topic_classifier_tool,
        facebook_post_writer_tool,
        post_to_facebook_page,
    ]


# Prompt cho agent đã được đơn giản hóa
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a content automation assistant. Follow these steps:
    1. Classify article topic using TopicClassifier
    2. If topic is 'Artificial Intelligence (AI)' or 'Web Development', continue. Otherwise STOP.
    3. Write Facebook post using FacebookPostWriter with format: 'article_text|||topic'
    4. Publish to Facebook using post_to_facebook_page tool

    IMPORTANT: 
    - Keep all inputs SHORT to avoid token limits
    - For FacebookPostWriter, use format: 'article_text|||topic' (separated by |||)
    - Process steps sequentially, don't skip any step
    - Only proceed if topic is AI or Web Development
    """),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

tools = get_tools()
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=6)


def run_agent_pipeline(article: str):
    # Truncate article nếu quá dài để tránh token limit
    if len(article) > 3000:
        article = article[:3000] + "..."
        print("⚠️  Article truncated to avoid token limit")

    goal = f"""
    Process this article step by step:

    Article: {article}

    Steps:
    1. Use TopicClassifier to classify the topic.
    2. Check if the topic is 'Artificial Intelligence (AI)' or 'Web Development'.
    3. If the topic is one of the above, use FacebookPostWriter to write a post with the format: '{article}|||[TOPIC_FROM_STEP_1]'.
    4. Use post_to_facebook_page to publish the post content from the previous step.

    Execute each step in order. Only proceed to the next step if the current one is successful.
    Stop immediately if the topic is not AI or Web Development.
    """

    try:
        result = agent_executor.invoke({"input": goal})
        return result
    except Exception as e:
        print(f"Pipeline error: {e}")
        return {"error": str(e)}

#
# # Test sample
# sample_article_content = """
# Python has become essential in AI and Data Science.
# Libraries like TensorFlow and PyTorch make machine learning accessible.
# Deep learning for image recognition and NLP is now easier than ever.
# """
#
# if __name__ == '__main__':
#     result = run_agent_pipeline(sample_article_content)
#     print("Pipeline result:", result)