# views.py

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
client = Groq(api_key=settings.GROQ_API_KEY)
model = "llama-3.3-70b-versatile"

@ensure_csrf_cookie
def chat_page(request):
    """Render the chat page and ensure that a CSRF cookie is set"""
    return render(request, 'chatbot.html')

def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # 1. Attempt to parse user's name
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

            for pattern in name_patterns:
                match = re.search(pattern, user_message, re.IGNORECASE)
                if match:
                    # For the last pattern, we need to swap first and last name
                    if ("last name" in pattern and 
                        "first name" in pattern and 
                        "last name" in pattern.split("first name")[0]):
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
                for rec in faiss_rag.records:
                    if rec["name"].lower() == full_name.lower():
                        user_record = rec
                        break

            # Direct name search in user message
            if not user_record:
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

            # 4. Construct retrieval-augmented context
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

            # -------------------------
            #  Enhanced final prompt:
            # -------------------------
            final_prompt = f"""
You are a helpful support chatbot for a retail/ecommerce company, with access to user data.

Your first steps whenever you speak to the user:
1. Greet the user politely.
2. Ask them for their name if you have not already gotten it.
3. Check if that user is in our database.
4. Mention that we can show their order history using a retrieval-augmented approach with FAISS.

Context:
{context_str}

User says: "{user_message}"

Important instructions:
1. If an EXACT USER MATCH is found, prioritize that information over similar users.
2. When a user explicitly asks to see their orders, show the orders from their exact match.
3. Do not discuss "Similar user" data at all.
4. When showing orders, format them in a clear, readable list.
5. Be friendly, efficient, and direct in your response.
"""

            # 5. Send final_prompt to the LLaMA model (via Groq)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": final_prompt}],
            )
            response_text = response.choices[0].message.content

            # 6. Return the model's text back to the frontend
            return JsonResponse({'response': response_text})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST method allowed'}, status=405)
