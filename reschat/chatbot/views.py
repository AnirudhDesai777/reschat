from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import re
import os

# 1. Import the Groq client
from groq import Groq

from .rag_utils import FaissRAG

# 2. Initialize the FaissRAG helper
faiss_rag = FaissRAG()

# 3. Initialize your Groq and define the model
client = Groq(api_key = settings.GROQ_API_KEY)
model = "llama-3.1-8b-instant"

@ensure_csrf_cookie
def chat_page(request):
    """Render the chat page and ensure that a CSRF cookie is set"""
    return render(request, 'chatbot.html')

def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # 1. Attempt to parse user's name - multiple regex patterns for different formats
            name_patterns = [
                # "My name is First Last"
                r"(?:my name is|i am|i'm)\s+([A-Za-z]+)\s+([A-Za-z]+)",
                # "First name X, last name Y"
                r"(?:first name|firstname)\s+([A-Za-z]+).*?(?:last name|lastname)\s+([A-Za-z]+)",
                # "Last name Y, first name X"
                r"(?:last name|lastname)\s+([A-Za-z]+).*?(?:first name|firstname)\s+([A-Za-z]+)"
            ]
            
            first_name = None
            last_name = None
            
            # Try each pattern
            for pattern in name_patterns:
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    # For the last pattern, we need to swap first and last name
                    if "last name" in pattern and "first name" in pattern and "last name" in pattern.split("first name")[0]:
                        last_name = match.group(1)
                        first_name = match.group(2)
                    else:
                        first_name = match.group(1)
                        last_name = match.group(2)
                    break
            
            # 2. If we have a user name, do a direct retrieval
            user_record = None
            if first_name and last_name:
                full_name = f"{first_name} {last_name}"
                # Case-insensitive search for the user
                for rec in faiss_rag.records:
                    if rec["name"].lower() == full_name.lower():
                        user_record = rec
                        break
            
            # Direct name search in user message (for messages like "show me Anirudh BM's orders")
            if not user_record:
                # Look for any full names in the user message
                name_in_text = re.findall(r'\b([A-Za-z]+)\s+([A-Za-z]+)\b', user_message)
                for first, last in name_in_text:
                    full_name = f"{first} {last}"
                    for rec in faiss_rag.records:
                        if rec["name"].lower() == full_name.lower():
                            user_record = rec
                            break
                    if user_record:
                        break

            # 3. Retrieve top-K similar user profiles
            top_similar = faiss_rag.find_similar_users(user_message, top_k=3)

            # 4. Construct a retrieval-augmented prompt
            context_snippets = []
            if user_record:
                context_snippets.append(
                    f"EXACT USER MATCH FOUND: {user_record['name']}, User ID: {user_record['id']}, Orders: {', '.join(user_record['orders'])}."
                )
            
            for dist, rec in top_similar:
                if rec:
                    # Skip if this is the same as the exact match
                    if user_record and rec['id'] == user_record['id']:
                        continue
                    snippet = f"Similar user: {rec['name']}, Orders: {', '.join(rec['orders'])}."
                    context_snippets.append(snippet)

            context_str = "\n".join(context_snippets)

            final_prompt = f"""
You are a helpful support chatbot for a retail/ecommerce company. You have access to some user data.

Context:
{context_str}

User says: "{user_message}"

Important instructions:
1. If an EXACT USER MATCH is found, prioritize that information over similar users.
2. When a user asks to see their orders or details, show them the orders from their exact match.
3. Do not discuss "Similar user" data under any case
4. When showing orders, format them in a clear, readable list.
5. Be helpful and direct - focus on answering the user's question clearly.

Respond in a friendly but efficient manner.
"""

            # 5. Call LLaMA (via Groq) with final_prompt
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": final_prompt}],
            )
            # Extract the generated text from the model's response
            response_text = response.choices[0].message.content

            # 6. Return LLaMA's response
            return JsonResponse({'response': response_text})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST method allowed'}, status=405)