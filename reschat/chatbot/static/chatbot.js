document.addEventListener('DOMContentLoaded', function() {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorAlert = document.getElementById('error-alert');
  
    // Focus input on page load
    userInput.focus();
  
    function addMessage(role, text) {
      const messageDiv = document.createElement('div');
      messageDiv.className = role === 'You' ? 'message user-message' : 'message bot-message';
      messageDiv.textContent = text;
      chatWindow.appendChild(messageDiv);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }
  
    function showLoading() {
      loadingIndicator.style.display = 'block';
      chatWindow.scrollTop = chatWindow.scrollHeight + 100;
    }
  
    function hideLoading() {
      loadingIndicator.style.display = 'none';
    }
  
    function showError(message = "Something went wrong. Please try again.") {
      errorAlert.textContent = message;
      errorAlert.classList.remove('d-none');
      setTimeout(() => {
        errorAlert.classList.add('d-none');
      }, 5000);
    }
  
    function sendMessage() {
      const message = userInput.value.trim();
      if(!message) return;
      
      // Clear input and add message to chat
      userInput.value = "";
      addMessage("You", message);
      
      // Show loading indicator
      showLoading();
      
      // Disable input while processing
      userInput.disabled = true;
      sendBtn.disabled = true;
  
      // Get the CSRF token from the cookie
      const csrftoken = getCookie('csrftoken');
      
      // Check if CSRF token exists
      if (!csrftoken) {
        hideLoading();
        showError("CSRF token missing. Please refresh the page.");
        userInput.disabled = false;
        sendBtn.disabled = false;
        return;
      }
  
      // Send the message to the backend
      fetch('/chat/api/', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ "message": message })
      })
      .then(response => {
        if (!response.ok) {
          if (response.status === 403) {
            throw new Error('CSRF verification failed. Please refresh the page.');
          }
          throw new Error('Network response was not ok: ' + response.status);
        }
        return response.json();
      })
      .then(data => {
        // Hide loading indicator
        hideLoading();
        
        // Add bot response
        if(data && data.response) {
          addMessage("Bot", data.response);
        } else if(data && data.error) {
          throw new Error(data.error);
        } else {
          throw new Error('Invalid response from server');
        }
      })
      .catch(err => {
        console.error('Error:', err);
        hideLoading();
        showError(err.message || "Failed to get response. Please try again.");
      })
      .finally(() => {
        // Re-enable input
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
      });
    }
  
    // Handle send button click
    sendBtn.addEventListener('click', sendMessage);
  
    // A more robust helper to get CSRF token from cookies
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
  
    // Make 'Enter' key work to send message
    userInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  
    // Log CSRF token status on load for debugging
    console.log('CSRF Token present:', getCookie('csrftoken') ? 'Yes' : 'No');
  });
  
  // Define a global function so it can be called from the HTML
  window.sendMessage = function() {
    const event = new Event('click');
    document.getElementById('send-btn').dispatchEvent(event);
  };