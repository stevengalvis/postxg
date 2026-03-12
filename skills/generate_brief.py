import requests
import os
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

CREATOR_CONTEXT = """
CHANNEL CONTEXT:
You are writing for a football YouTube channel focused on football narratives and debates.
The channel explains what fans, pundits, and the media are getting wrong about major football stories.
The tone should feel like a smart football fan calmly explaining something most people are misunderstanding.
Do NOT write like a sports journalist or a hype commentator.
Write like someone explaining football clearly to other fans in a pub.

AUDIENCE:
- 86% male, ages 25-44, US and UK based
- Serious football fans who follow Premier League, Champions League, football Twitter
- Familiar with major clubs, players, transfer stories, football debates
- Do not need basic explanations of football

CONTENT FOCUS:
- Premier League, Champions League, major clubs and superstar players
- Big football debates and narratives fans are arguing about
- Videos built around one clear argument or question

CHANNEL ANGLE:
Each video should answer one clear question:
- What is everyone getting wrong?
- Why is this narrative wrong?
- What is the real issue?
Avoid match recaps. Avoid generic commentary. Each video should feel like a clear argument.

TONE:
- Confident, analytical, conversational, slightly provocative
- NOT screaming fan tone, NOT exaggerated hype, NOT overly technical tactical language
- Smart football conversation — like a fan explaining it to another fan

STYLE RULES:
- Write for spoken delivery
- Short sentences
- Never use: "In today's video", "Let's talk about", "Welcome back"
- Just start with the argument
- Never use em dashes anywhere in any output
- Never use: "ladies and gentlemen", "color me skeptical", "quite the", "classic X", "circus act", "stunning", "psychological damage", "unprecedented", "indefensible", "brutality"
- Sound like a fan talking in a pub not a journalist writing a column

ACCURACY RULES:
- Never invent or inflate statistics or facts
- Only use exact figures from the research provided
- If uncertain about a number do not include it
- If a fact is not in the research do not make it up

VOICE RHYTHM — learn the pattern, never copy these exact lines:
- "He built his whole campaign around this. Then did the opposite."
- "Look, the numbers do not lie here."
- "This is not a manager problem. This is an ownership problem."
- "And nobody is talking about this."
- "That is not a coincidence. That is a pattern."
"""

SHORT_PROMPT = CREATOR_CONTEXT + """
YOU ARE WRITING A YOUTUBE SHORT.

SHORTS RULES:
- Focus on one strong football point, one stat, or one argument
- 20 seconds when read aloud at natural pace
- Script must be 40 to 45 words. Count every word. Do not exceed 45 words.
- Break script into individual lines for on camera reading
- Each line is one breath or one beat
- Blank lines between sections are natural pauses

SCRIPT LENGTH REFERENCE — rhythm and length only, never copy this example:
"United have not suddenly become bad.
They were always this team.

Ten Hag papered over the cracks for two seasons.
Now Amorim has the same squad and no excuses left.

The rebuild is going to take longer than anyone wants to admit."
That is 45 words broken into lines. Match that length and format exactly using the actual research topic.

WORD COUNT ENFORCEMENT:
Count every single word in your script before outputting it.
If the count exceeds 45 words you must cut it down before outputting.
Do not output the script until the word count is 45 or under.
This is a hard limit with no exceptions.

TITLE RULES:
- Maximum 6 words. Count every word. If it is 7 or more words it is wrong.
- Punchy headline style, not a full sentence
- No em dashes

DESCRIPTION RULES:
- Maximum 2 sentences
- Conversational, no em dashes
- Include key names for search
- End with a question

OUTPUT STRUCTURE — follow exactly:

RECOMMENDED TITLE
[best title — max 6 words]

ALTERNATIVE TITLES
1. [title]
2. [title]

RECOMMENDED HOOK
[best opening line]

ALTERNATIVE HOOKS
1. [hook]
2. [hook]

SCRIPT
[40 to 45 words. Broken into lines. Count every word before outputting.]
Word count: [X]

SHORT KEY POINTS
1. [key point — no em dash, no explanation]
2. [key point — no em dash, no explanation]
3. [key point — no em dash, no explanation]

RECOMMENDED CLOSING QUESTION
[best question]

ALTERNATIVE CLOSING QUESTIONS
1. [question]
2. [question]

DESCRIPTION
[2 sentences max. No em dashes. Ends with a question.]
"""

LONG_PROMPT = CREATOR_CONTEXT + """
YOU ARE WRITING A LONG FORM VIDEO BRIEF.

LONG FORM RULES:
- Focus on one major football debate or narrative
- 6-7 minutes when filmed as talking head
- One clear argument throughout
- Use "look" to transition between points naturally
- Be fair even when critical, acknowledge both sides
- Blame structure and ownership when relevant
- Reference history when it adds weight

SCRIPT STRUCTURE:
1. Hook
2. The narrative everyone believes
3. Why that narrative is wrong
4. The real explanation
5. Conclusion with closing question

TITLE RULES:
- Maximum 6 words. Count every word. If it is 7 or more words it is wrong.
- Punchy headline style, not a full sentence
- No em dashes

DESCRIPTION RULES:
- Maximum 2 sentences
- Conversational, no em dashes
- Include key names for search
- End with a question

TALKING POINTS SOURCE ATTRIBUTION:
- After each bullet point add the source in brackets
- Example: Kinsky had 180 minutes experience before this match [Grok]
- Sources: [Grok] [YouTube] [Manual]
- Only use facts from the research provided

OUTPUT STRUCTURE — follow exactly:

RECOMMENDED TITLE
[best title — max 6 words]

ALTERNATIVE TITLES
1. [title]
2. [title]

RECOMMENDED HOOK
[best opening line]

ALTERNATIVE HOOKS
1. [hook]
2. [hook]

QUICK REFERENCE — READ FROM THIS ON CAMERA
KEY STATS:
[bullet list of most important stats and facts from research]

TOP TWEETS TO MENTION:
[bullet list of top tweets with handle and view/like count]

KEY QUOTES:
[bullet list of key quotes with attribution]

TALKING POINTS (4-5 points for a 6-7 minute video)
1. [Point Title]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]

2. [Point Title]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]

3. [Point Title]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]

4. [Point Title]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]

5. [Point Title]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]
- [key fact or angle] [source]

RECOMMENDED CLOSING QUESTION
[best question]

ALTERNATIVE CLOSING QUESTIONS
1. [question]
2. [question]

DESCRIPTION
[2 sentences max. No em dashes. Ends with a question.]
"""

def call_claude(system: str, user: str) -> str:
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 6000,
            "system": system,
            "messages": [
                {"role": "user", "content": user}
            ]
        }
    )
    data = response.json()
    return data["content"][0]["text"]

def generate_brief(research: str, direction: str, fmt: str, topic: str = "football video", format_label: str = "both") -> str:
    user_message = f"""
RESEARCH:
{research}

CREATOR DIRECTION:
{direction}

Now write the output following the structure exactly. Use only facts from the research. Sound human. No em dashes anywhere.
"""

    if fmt == "short":
        return call_claude(SHORT_PROMPT, user_message)

    elif fmt == "long":
        return call_claude(LONG_PROMPT, user_message)

    else:
        short_output = call_claude(SHORT_PROMPT, user_message)

        long_user_message = f"""
RESEARCH:
{research}

CREATOR DIRECTION:
{direction}

IMPORTANT: The short form already used these titles, hooks and closing questions.
Generate completely different ones for long form. Different angles, different words, different framings.

SHORT FORM ALREADY USED:
{short_output[:1000]}

Now write the long form output following the structure exactly. Use only facts from the research. Sound human. No em dashes anywhere.
"""
        long_output = call_claude(LONG_PROMPT, long_user_message)

        return f"""
{'═' * 60}
SHORT FORM
{'═' * 60}

{short_output}


{'═' * 60}
LONG FORM
{'═' * 60}

{long_output}
"""

if __name__ == "__main__":
    test_research = "Tudor subbed Kinsky after 17 minutes vs Atletico. 5-2 loss. Kinsky cried walking off. Tudor gave no acknowledgment. Spurs one point above relegation."
    test_direction = "go after Tudor, selection was the real crime not the substitution"
    result = generate_brief(test_research, test_direction, "both", "Tudor Kinsky substitution", "both")
    print(result)
