from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from openai import OpenAI
from datetime import datetime

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)
model = "gpt-4o"

# Pricing constants
BASE_PRICE = 99.99
EXTRA_LARGE_PRICE = 37.99
LARGE_PRICE = 28.99
BAGS_PRICE = 7.99
FUEL_FEE = 12.39
BOOKING_FEE = 18.00

def calculate_estimated_pickup_cost(items):
    """Calculate the estimated pickup cost based on selected items."""
    extra_large = items.get('extra_large', 0)
    large = items.get('large', 0)
    bags = items.get('bags', 0)
    cost = (BASE_PRICE +
            extra_large * EXTRA_LARGE_PRICE +
            large * LARGE_PRICE +
            bags * BAGS_PRICE +
            FUEL_FEE)
    return cost

def generate_confirmation_message(data):
    """Generate a formatted confirmation message from reservation data."""
    items = data.get('items', {})
    address = data.get('address', '')
    time_slot = data.get('time_slot', '')
    
    estimated_pickup_cost = calculate_estimated_pickup_cost(items)
    total_cost = estimated_pickup_cost + BOOKING_FEE
    
    items_str = ", ".join([f"{key.replace('_', ' ').title()}: {value}" for key, value in items.items()])
    message = (
        f"🎉 Great choice! Here are your reservation details:\n\n"
        f"📅 Pickup Date & Time: {time_slot}\n"
        f"📍 Pickup Address: {address}\n"
        f"📦 Items: {items_str}\n\n"
        f"💰 Estimated Pickup Cost (Due On-Site): ${estimated_pickup_cost:.2f}\n"
        f"💸 Booking Fee (Due Today): ${BOOKING_FEE:.2f}\n"
        f"💵 Total Cost: ${total_cost:.2f}\n\n"
        f"To secure this fantastic deal, simply type 'confirm' to finalize your reservation. "
        f"Want to adjust? Type 'change items' or 'change schedule'!"
    )
    return message

@ensure_csrf_cookie
def chat_page(request):
    """Render the chat page and initialize session state."""
    if 'state' not in request.session:
        request.session['state'] = 'items'
        request.session['reservation_data'] = {}
    return render(request, 'chatbot.html')

def chat_api(request):
    """Handle chat API requests for the donation pickup reservation flow."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    data = json.loads(request.body)
    user_message = data.get('message', '').strip()

    # Initialize session if not present
    if 'state' not in request.session:
        request.session['state'] = 'items'
        request.session['reservation_data'] = {}

    state = request.session['state']

    # Handle initial message on page load
    if user_message == "init":
        if state == 'items':
            response_text = (
                "🌟 Welcome to ReSupply! Let’s get started with your donation pickup. "
                "Tell me about the amazing items you’d like to donate—include types and quantities, "
                "e.g., '2 large items, 3 bags of clothes' or '1 sofa and 2 large boxes.' "
                "The more you donate, the bigger your impact! I’m here to make this process smooth and rewarding for you."
            )
        elif state == 'schedule':
            response_text = (
                "Awesome! You’re one step closer. Please share your pickup address and preferred date/time, "
                "e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM.' "
                "We’ll find the perfect slot to suit your schedule—let’s make it happen!"
            )
        elif state == 'confirmation':
            response_text = generate_confirmation_message(request.session['reservation_data'])
        else:
            response_text = (
                "🎉 Your reservation is complete! Thank you for choosing ReSupply. "
                "How else can I assist you today? Need more donation ideas or support?"
            )
        return JsonResponse({'response': response_text})

    # Process user message based on current state
    if state == 'items':
        prompt = (
            "You are a helpful and sales-oriented assistant for ReSupply, a donation pickup service. "
            "Extract the item types and quantities from the user's message: '{user_message}'. "
            "Map items to categories: 'sofa', 'box', or 'boxes' as 'extra_large', 'large item' or 'large' as 'large', "
            "'bag' or 'bags' as 'bags'. Respond with a JSON object where keys are 'extra_large', 'large', 'bags' "
            "and values are integers representing quantities. If no valid items are mentioned or the input is unclear, "
            "suggest they provide details like '2 large items, 3 bags of clothes' or '1 sofa and 2 large boxes' "
            "to maximize their donation impact, and ask them to try again."
        )
        model_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt.format(user_message=user_message)}]
        )
        extracted_text = model_response.choices[0].message.content

        try:
            items = json.loads(extracted_text)
            if items and all(k in ['extra_large', 'large', 'bags'] and isinstance(v, int) for k, v in items.items()):
                request.session['reservation_data']['items'] = items
                request.session['state'] = 'schedule'
                response_text = (
                    "Fantastic selection! You’re making a difference. "
                    "Now, please share your pickup address and preferred date/time, "
                    "e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM.' "
                    "Let’s schedule this at your convenience!"
                )
            else:
                response_text = (
                    "I couldn’t quite identify your items. Please list them clearly, e.g., "
                    "'2 large items, 3 bags of clothes' or '1 sofa and 2 large boxes,' "
                    "so we can get you started on this rewarding journey! Try again."
                )
        except json.JSONDecodeError:
            response_text = (
                "Hmm, I couldn’t process that. Please list your items clearly, e.g., "
                "'2 large items, 3 bags of clothes' or '1 sofa and 2 large boxes,' "
                "to help us maximize your impact. Please try again."
            )

    elif state == 'schedule':
        prompt = (
            "You are a helpful and sales-oriented assistant for ReSupply. "
            "Extract the address and preferred date/time from the user's message: '{user_message}'. "
            "Respond with a JSON object with keys 'address' and 'time_slot'. The time_slot should be "
            "in a natural date/time format (e.g., 'April 20, 2025 - 10 AM'). If the input is invalid or incomplete, "
            "encourage them to provide both address and date/time, e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM,' "
            "and highlight the convenience of flexible scheduling."
        )
        model_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt.format(user_message=user_message)}]
        )
        extracted_text = model_response.choices[0].message.content

        try:
            data = json.loads(extracted_text)
            address = data.get('address', '')
            time_slot = data.get('time_slot', '')
            if address and time_slot:
                try:
                    datetime.strptime(time_slot.split(' - ')[0], '%B %d, %Y')
                    request.session['reservation_data']['address'] = address
                    request.session['reservation_data']['time_slot'] = time_slot
                    request.session['state'] = 'confirmation'
                    response_text = generate_confirmation_message(request.session['reservation_data'])
                except ValueError:
                    response_text = (
                        "Oops, that date doesn’t look right. Please provide your address and date/time, "
                        "e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM.' "
                        "We’re flexible—pick a time that works for you!"
                    )
            else:
                response_text = (
                    "Almost there! Please include both your address and preferred date/time, "
                    "e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM.' "
                    "Let’s find the perfect slot to make your donation seamless!"
                )
        except json.JSONDecodeError:
            response_text = (
                "I couldn’t parse that. Please provide your address and date/time clearly, "
                "e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM.' "
                "We’re here to make this easy and convenient for you!"
            )

    elif state == 'confirmation':
        message_lower = user_message.lower()
        if "confirm" in message_lower:
            response_text = (
                "🎉 Excellent decision! Your reservation is confirmed with ReSupply. "
                "Thank you for your generous donation—we’re thrilled to help you make an impact. "
                "Need more assistance or another pickup? Let me know!"
            )
            request.session['state'] = 'done'
        elif "change items" in message_lower:
            request.session['state'] = 'items'
            response_text = (
                "Great choice to adjust! Please tell me the new items you’d like to donate, "
                "e.g., '2 large items, 3 bags of clothes' or '1 sofa and 2 large boxes.' "
                "Let’s maximize your contribution!"
            )
        elif "change schedule" in message_lower:
            request.session['state'] = 'schedule'
            response_text = (
                "Let’s tweak that schedule! Please provide your new address and date/time, "
                "e.g., '87 Sheridan Street, Jamaica Plain, MA 02130, April 20, 2025 - 10 AM.' "
                "We’ll find the perfect fit!"
            )
        else:
            response_text = (
                "Please type 'confirm' to lock in this amazing deal, 'change items' to update your donation, "
                "or 'change schedule' to adjust your pickup time. We’re excited to assist!"
            )

    else:  # state == 'done'
        response_text = (
            "🎉 Your reservation is complete! Thank you for choosing ReSupply. "
            "Ready for another donation or need support? I’m here to help!"
        )

    return JsonResponse({'response': response_text})