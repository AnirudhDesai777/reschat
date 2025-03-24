from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
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

def chat_page(request):
    return render(request, 'chatbot.html')

def chat_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '')

        # 1. Attempt to parse user’s name
        name_regex = r"(?:i'm|i am|my name is)\s+([A-Za-z]+)\s+([A-Za-z]+)"
        match = re.search(name_regex, user_message, re.IGNORECASE)

        first_name = None
        last_name = None
        if match:
            first_name = match.group(1)
            last_name = match.group(2)

        # 2. If we have a user name, do a direct retrieval
        user_record = None
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
            for rec in faiss_rag.records:
                if rec["name"].lower() == full_name.lower():
                    user_record = rec
                    break

        # 3. Retrieve top-K similar user profiles
        top_similar = faiss_rag.find_similar_users(user_message, top_k=3)

        # 4. Construct a retrieval-augmented prompt
        context_snippets = []
        if user_record:
            context_snippets.append(
                f"User Found: {user_record['name']}, Orders: {', '.join(user_record['orders'])}."
            )
        for dist, rec in top_similar:
            if rec:
                snippet = f"Similar user: {rec['name']}, Orders: {', '.join(rec['orders'])}."
                context_snippets.append(snippet)

        context_str = "\n".join(context_snippets)

        final_prompt = f"""
You are a helpful support chatbot. You have access to some user data. 
Context:
{context_str}

User says: "{user_message}"

Respond helpfully, using relevant user context.
"""

        # 5. Call LLaMA (via Groq) with final_prompt
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": final_prompt}],
        )
        # Extract the generated text from the model’s response
        response_text = response.choices[0].message.content

        # 6. Return LLaMA’s response
        return JsonResponse({'response': response_text})

    return JsonResponse({'error': 'Only POST method allowed'}, status=405)
